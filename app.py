# app.py
import base64
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

from config.settings import APP_SUBTITLE, APP_TITLE
from core.cache import df_manager
from core.data_quality import normalize_dataframe_types
from core.data_loader import load_data
from core.global_filters import apply_global_filters
from ui.sidebar import render as render_sidebar
from ui.style import style_css

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "logo" / "NEXUS.jpeg"


def ensure_unique_dataframe_columns(df):
    seen = {}
    used = set()
    new_cols = []
    renamed = []

    for original in df.columns.tolist():
        base = str(original)
        count = seen.get(base, 0) + 1
        seen[base] = count

        if count == 1 and base not in used:
            candidate = base
        else:
            suffix = count
            candidate = f"{base}__{suffix}"
            while candidate in used:
                suffix += 1
                candidate = f"{base}__{suffix}"

        used.add(candidate)
        new_cols.append(candidate)
        if candidate != base:
            renamed.append((base, candidate))

    if not renamed and all(str(col) == col for col in df.columns.tolist()):
        return df, []

    out = df.copy()
    out.columns = new_cols
    return out, renamed


def _safe_as_series(df: pd.DataFrame, col: str) -> pd.Series:
    selected = df.loc[:, col]
    if isinstance(selected, pd.DataFrame):
        return selected.iloc[:, 0]
    return selected


def safe_compute_metric_by_dimension(
    df: pd.DataFrame,
    dimension_col: str,
    metric_type: str,
    measure_name: str,
    target_col: str | None,
    numerator_col: str | None,
    denominator_col: str | None,
) -> pd.DataFrame:
    dim_series = _safe_as_series(df, dimension_col)
    work = pd.DataFrame({"__dim__": dim_series}, index=df.index)

    if metric_type == "Ratio":
        work["__num__"] = pd.to_numeric(_safe_as_series(df, numerator_col), errors="coerce")
        work["__den__"] = pd.to_numeric(_safe_as_series(df, denominator_col), errors="coerce")
        grouped = work.groupby("__dim__", dropna=False)
        numerator = grouped["__num__"].sum(min_count=1)
        denominator = grouped["__den__"].sum(min_count=1)
        values = numerator / denominator.replace(0, pd.NA)
    else:
        work["__val__"] = _safe_as_series(df, target_col)
        if metric_type in {"Somme", "Moyenne", "Minimum", "Maximum"}:
            work["__val__"] = pd.to_numeric(work["__val__"], errors="coerce")

        grouped = work.groupby("__dim__", dropna=False)["__val__"]
        if metric_type == "Somme":
            values = grouped.sum(min_count=1)
        elif metric_type == "Moyenne":
            values = grouped.mean()
        elif metric_type == "Minimum":
            values = grouped.min()
        elif metric_type == "Maximum":
            values = grouped.max()
        elif metric_type == "Nombre de valeurs":
            values = grouped.count()
        elif metric_type == "Nombre distinct":
            values = grouped.nunique(dropna=True)
        else:
            return pd.DataFrame(columns=[dimension_col, measure_name])

    result = values.reset_index(name=measure_name).rename(columns={"__dim__": dimension_col})
    result[measure_name] = pd.to_numeric(result[measure_name], errors="coerce")
    result[dimension_col] = result[dimension_col].astype("string").fillna("(Vide)")
    return result


def render_circular_logo(path: Path, size_px: int = 120) -> None:
    if not path.exists():
        raise FileNotFoundError

    image_bytes = path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    suffix = path.suffix.lower()
    mime_type = "image/png" if suffix == ".png" else "image/webp" if suffix == ".webp" else "image/jpeg"

    st.markdown(
        f"""
        <div style="
            width: {size_px}px;
            height: {size_px}px;
            border-radius: 50%;
            overflow: hidden;
            margin: 0 auto;
            border: 2px solid rgba(148, 163, 184, 0.45);
        ">
            <img
                src="data:{mime_type};base64,{encoded}"
                alt="Logo"
                style="width: 100%; height: 100%; object-fit: cover;"
            />
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_data_quality_feedback(report: dict | None) -> None:
    if not report:
        return

    numeric_converted = report.get("numeric_converted", [])
    datetime_converted = report.get("datetime_converted", [])
    forced_string = report.get("forced_string", [])
    suspect_columns = report.get("suspect_columns", [])
    total_changes = len(numeric_converted) + len(datetime_converted) + len(forced_string)

    if total_changes == 0 and not suspect_columns:
        return

    with st.expander("Qualite des types au chargement", expanded=False):
        if numeric_converted:
            st.write("Conversion en numerique:", ", ".join(f"`{col}`" for col in numeric_converted))
        if datetime_converted:
            st.write("Conversion en date:", ", ".join(f"`{col}`" for col in datetime_converted))
        if forced_string:
            st.write(
                "Conversion en texte (types melanges detectes):",
                ", ".join(f"`{col}`" for col in forced_string),
            )
        if suspect_columns:
            preview = pd.DataFrame(
                [
                    {
                        "Colonne": item.get("column"),
                        "Types observes": ", ".join(item.get("types", [])),
                        "Ratio numerique": item.get("numeric_ratio"),
                        "Ratio date": item.get("datetime_ratio"),
                    }
                    for item in suspect_columns[:12]
                ]
            )
            st.caption("Colonnes partiellement convertibles (verification recommandee):")
            st.dataframe(preview, width="stretch")


def _build_data_slide_uri(title: str, color_a: str, color_b: str) -> str:
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="{color_a}" />
          <stop offset="100%" stop-color="{color_b}" />
        </linearGradient>
      </defs>
      <rect width="640" height="360" fill="url(#bg)" rx="20" />
      <g opacity="0.16" fill="#ffffff">
        <circle cx="94" cy="72" r="42" />
        <circle cx="520" cy="278" r="64" />
      </g>
      <polyline points="50,240 130,200 210,220 290,150 370,170 450,120 530,90 610,110"
                fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round"/>
      <g fill="#ffffff" opacity="0.82">
        <rect x="80" y="190" width="26" height="90" rx="8" />
        <rect x="128" y="160" width="26" height="120" rx="8" />
        <rect x="176" y="210" width="26" height="70" rx="8" />
        <rect x="224" y="150" width="26" height="130" rx="8" />
      </g>
      <text x="38" y="54" font-size="28" font-family="Inter, Arial, sans-serif" fill="#ffffff" font-weight="700">
        {title}
      </text>
      <text x="40" y="320" font-size="16" font-family="Inter, Arial, sans-serif" fill="#ffffff" opacity="0.9">
        Data Analytics Pro - Visualisation en continu
      </text>
    </svg>
    """
    return f"data:image/svg+xml;utf8,{quote(svg)}"


def render_app_presentation() -> None:
    slides = [
        ("Exploration des donnees", "#0f172a", "#1d4ed8"),
        ("Nettoyage intelligent", "#1f2937", "#0e7490"),
        ("Modeles & prediction", "#312e81", "#1d4ed8"),
        ("Indicateurs DAX", "#134e4a", "#115e59"),
        ("Recherche & edition", "#374151", "#111827"),
    ]
    cards = [
        {
            "title": title,
            "uri": _build_data_slide_uri(title, color_a, color_b),
        }
        for title, color_a, color_b in slides
    ]
    doubled_cards = cards + cards
    cards_html = "".join(
        f"""
        <div class="nexus-slide">
          <img src="{card["uri"]}" alt="{card["title"]}" />
          <div class="nexus-slide-title">{card["title"]}</div>
        </div>
        """
        for card in doubled_cards
    )

    st.markdown(
        f"""
        <style>
          .nexus-carousel-wrap {{
            overflow: hidden;
            width: 100%;
            margin-top: 0.25rem;
            margin-bottom: 1rem;
            border-radius: 16px;
          }}
          .nexus-carousel-track {{
            display: flex;
            gap: 14px;
            width: max-content;
            animation: nexus-scroll 48s linear infinite;
          }}
          .nexus-slide {{
            width: 330px;
            flex: 0 0 auto;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 16px;
            overflow: hidden;
          }}
          .nexus-slide img {{
            width: 100%;
            height: 180px;
            object-fit: cover;
            display: block;
          }}
          .nexus-slide-title {{
            padding: 10px 12px 12px 12px;
            font-size: 0.92rem;
            font-weight: 600;
            color: #ffffff;
            letter-spacing: 0.01em;
          }}
          @keyframes nexus-scroll {{
            from {{ transform: translateX(0); }}
            to {{ transform: translateX(-50%); }}
          }}
          @media (max-width: 768px) {{
            .nexus-slide {{
              width: 280px;
            }}
            .nexus-slide img {{
              height: 155px;
            }}
          }}
        </style>
        <div class="nexus-carousel-wrap">
          <div class="nexus-carousel-track">
            {cards_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## NEXUS DATA ANALYTICS PRO")
    st.markdown("### Engineering Intelligence. Empowering Decisions.")
    st.markdown("Une nouvelle generation de plateforme analytique.")

    st.markdown(
        """
Dans un environnement ou la donnee est devenue un actif strategique, **Nexus Data Analytics Pro** offre une infrastructure analytique complete permettant de transformer des volumes complexes d'informations en decisions claires, mesurables et performantes.

Concue par **M. NGOMAYILLA NDEMA Christopher**, expert en ingenierie analytique et responsable du groupe **NEXUS**, la plateforme allie rigueur scientifique, intelligence artificielle et excellence technologique.

🌍 **Une plateforme. Une vision. Une maitrise totale de la donnee.**

Nexus Data Analytics Pro n'est pas un simple outil d'analyse.

C'est un environnement integre qui couvre l'ensemble du cycle de vie des donnees:

- Acquisition
- Preparation
- Modelisation
- Analyse avancee
- Intelligence predictive
- Reporting strategique

## ⚙️ Architecture Modulaire Haute Performance

### 1️⃣ Executive Dashboard
Visualisation instantanee des indicateurs cles.

- Statistiques descriptives automatisees
- Analyse de qualite des donnees
- Correlations intelligentes
- Exports professionnels

Une vue decisionnelle immediate.

### 2️⃣ Advanced Analytics Engine
Puissance statistique integree.

- Analyses univariees, bivariees, multivariees
- Visualisations interactives dynamiques
- Exploration correlationnelle avancee

Comprendre les relations invisibles dans vos donnees.

### 3️⃣ Data Engineering Suite
Maitrise totale de la qualite des donnees.

- Detection intelligente des incoherences
- Traitement avance des valeurs manquantes
- Typage automatique securise
- Journalisation complete des modifications

Des donnees fiables. Des analyses solides.

### 4️⃣ Artificial Intelligence & Machine Learning
Intelligence integree a votre strategie.

- Modeles supervises (classification, regression)
- Modeles non supervises (clustering, segmentation)
- Evaluation metrique complete
- Visualisation interpretable des performances

Passez de l'analyse descriptive a la prediction strategique.

### 5️⃣ Business Intelligence & DAX Modeling
Pont direct vers l'ecosysteme BI.

- Generation automatisee de mesures DAX
- Bibliotheque de modeles analytiques
- Simulation logique type Power BI
- Export de scripts prets a deployer

Un moteur BI integre a votre workflow Python.

### 6️⃣ Smart Data Control
Edition securisee et tracable.

- Filtres simples et croises
- Modification controlee des enregistrements
- Systeme Undo / Redo
- Historique complet des actions

Un controle absolu, sans perte d'integrite.

### 7️⃣ Professional Reporting
Communication analytique optimisee.

- Rapports PDF premium
- Export Excel structure
- Dossiers analytiques prets a presentation

Transformez vos analyses en livrables executifs.

## 🎯 Positionnement Strategique

Nexus Data Analytics Pro s'adresse a:

- Organisations publiques et privees
- Cabinets financiers et comptables
- Data analysts et data scientists
- Centres de recherche
- Universites et ecoles specialisees

## 🔐 Philosophie

Rigueur scientifique.  
Clarte decisionnelle.  
Automatisation intelligente.  
Securite des donnees.

## 💡 Notre ambition

Creer une plateforme capable de rivaliser avec les standards internationaux en matiere d'analyse decisionnelle, tout en restant accessible, modulaire et evolutive.
        """
    )


# Initialisation du compteur global pour les cles uniques des graphiques
if "plot_counter" not in st.session_state:
    st.session_state.plot_counter = 0

# Configuration de la page
st.set_page_config(
    page_title=f"{APP_TITLE} - {APP_SUBTITLE}",
    page_icon=LOGO_PATH,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Theme dynamique
theme = st.session_state.get("theme", "dark")
style_css(theme)

# Sidebar: retourne le fichier charge
uploaded_file = render_sidebar()

# Chargement et persistance des donnees
if "df" not in st.session_state:
    st.session_state.df = None

if uploaded_file is not None:
    with st.spinner("Chargement du fichier en cours..."):

        @st.cache_data(show_spinner=False)
        def load_cached(_file):
            return load_data(_file)

        raw_df = load_cached(uploaded_file)
        if raw_df is not None:
            typed_df, quality_report = normalize_dataframe_types(raw_df)
            normalized_df, renamed_cols = ensure_unique_dataframe_columns(typed_df)
            st.session_state.df = df_manager(normalized_df)
            st.session_state.data_quality_report = quality_report
            st.success(
                f"Fichier {uploaded_file.name} charge avec succes "
                f"({len(raw_df):,} lignes x {len(raw_df.columns)} colonnes)."
            )
            if renamed_cols:
                preview = ", ".join(f"`{old}` -> `{new}`" for old, new in renamed_cols[:6])
                if len(renamed_cols) > 6:
                    preview += f", ... (+{len(renamed_cols) - 6})"
                st.warning(
                    "Colonnes dupliquees detectees dans le fichier source. "
                    "Des noms uniques ont ete appliques pour eviter les erreurs de calcul: "
                    f"{preview}"
                )
            if quality_report.get("forced_string"):
                st.warning(
                    "Certaines colonnes ont ete forcees en texte (types heterogenes) "
                    "pour eviter les erreurs d'affichage/filtrage."
                )

df = st.session_state.df

# Titre avec logo
col1, col2 = st.columns([1, 5])
with col1:
    try:
        render_circular_logo(LOGO_PATH, size_px=120)
    except FileNotFoundError:
        st.markdown("### Logo")

with col2:
    st.title(APP_TITLE)
    st.subheader(APP_SUBTITLE)

render_app_presentation()
render_data_quality_feedback(st.session_state.get("data_quality_report"))

if df is None:
    st.info("Utilisez la barre laterale pour charger un fichier et demarrer l'analyse.")
    st.stop()

# Navigation principale (selecteur unique pour eviter le masquage des onglets)
module_options = [
    "Tableau de bord",
    "Analyses",
    "Preparation des donnees",
    "Machine Learning",
    "Modelisation DAX",
    "Recherche et edition",
    "Rapports et exports",
]
selected_module = st.selectbox("Module", module_options, index=0, key="main_module_select")
module_df = df
if selected_module != "Preparation des donnees":
    module_df, filter_meta = apply_global_filters(df, prefix="global_filter")
    if filter_meta.get("enabled"):
        st.caption(
            f"Filtres globaux actifs: {filter_meta.get('active_filters', 0)} | "
            f"Lignes visibles: {len(module_df):,}/{len(df):,}"
        )

if selected_module == "Tableau de bord":
    from pages.dashboard import main as dashboard_main

    dashboard_main(module_df)
elif selected_module == "Analyses":
    from pages.analyse import main as analyse_main

    analyse_main(module_df)
elif selected_module == "Preparation des donnees":
    from pages.cleaning import main as cleaning_main

    cleaning_main(df)
elif selected_module == "Machine Learning":
    from pages.ml import main as ml_main

    ml_main(module_df)
elif selected_module == "Modelisation DAX":
    import pages.dax as dax_module

    # Defensive runtime patch: keeps DAX grouping safe even if an old module
    # version is still loaded by the deployment cache.
    dax_module._compute_metric_by_dimension = safe_compute_metric_by_dimension
    dax_module.main(module_df)
elif selected_module == "Recherche et edition":
    from pages.data_editor import main as data_editor_main

    data_editor_main(module_df)
else:
    from pages.export import main as export_main

    export_main(module_df)

# Footer
st.markdown("---")
st.caption("(c) 2025 Data Analytics Pro - Developpe avec Streamlit")

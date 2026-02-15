# app.py
import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from config.settings import APP_SUBTITLE, APP_TITLE
from core.cache import df_manager
from core.data_loader import load_data
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
            normalized_df, renamed_cols = ensure_unique_dataframe_columns(raw_df)
            st.session_state.df = df_manager(normalized_df)
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

if selected_module == "Tableau de bord":
    from pages.dashboard import main as dashboard_main

    dashboard_main(df)
elif selected_module == "Analyses":
    from pages.analyse import main as analyse_main

    analyse_main(df)
elif selected_module == "Preparation des donnees":
    from pages.cleaning import main as cleaning_main

    cleaning_main(df)
elif selected_module == "Machine Learning":
    from pages.ml import main as ml_main

    ml_main(df)
elif selected_module == "Modelisation DAX":
    import pages.dax as dax_module

    # Defensive runtime patch: keeps DAX grouping safe even if an old module
    # version is still loaded by the deployment cache.
    dax_module._compute_metric_by_dimension = safe_compute_metric_by_dimension
    dax_module.main(df)
elif selected_module == "Recherche et edition":
    from pages.data_editor import main as data_editor_main

    data_editor_main(df)
else:
    from pages.export import main as export_main

    export_main(df)

# Footer
st.markdown("---")
st.caption("(c) 2025 Data Analytics Pro - Developpe avec Streamlit")

# app.py
import base64
from pathlib import Path

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
    from pages.dax import main as dax_main

    dax_main(df)
elif selected_module == "Recherche et edition":
    from pages.data_editor import main as data_editor_main

    data_editor_main(df)
else:
    from pages.export import main as export_main

    export_main(df)

# Footer
st.markdown("---")
st.caption("(c) 2025 Data Analytics Pro - Developpe avec Streamlit")

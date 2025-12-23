# app.py
import streamlit as st
from config.settings import APP_TITLE, APP_SUBTITLE
from ui.sidebar import render as render_sidebar
from core.cache import df_manager
from core.data_loader import load_data
from ui.style import style_css
from pathlib import Path

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "logo" / "NEXUS.jpeg"


# === Initialisation du compteur global pour keys uniques des graphiques ===
if 'plot_counter' not in st.session_state:
    st.session_state.plot_counter = 0

# Configuration de la page
st.set_page_config(
    page_title=f"{APP_TITLE} - {APP_SUBTITLE}",
    page_icon=LOGO_PATH,
    layout="wide",
    initial_sidebar_state="expanded"
)


# Thème dynamique
theme = st.session_state.get("theme", "dark")
style_css(theme)

# Sidebar – retourne l'uploaded_file
uploaded_file = render_sidebar()

# Chargement et persistance des données
if 'df' not in st.session_state:
    st.session_state.df = None

if uploaded_file is not None:
    with st.spinner("Chargement du fichier en cours..."):
        @st.cache_data(show_spinner=False)
        def load_cached(_file):
            return load_data(_file)

        raw_df = load_cached(uploaded_file)
        if raw_df is not None:
            st.session_state.df = df_manager(raw_df)
            st.success(f"✅ {uploaded_file.name} chargé avec succès ! ({len(raw_df):,} lignes × {len(raw_df.columns)} colonnes)")

df = st.session_state.df

# Titre avec logo
col1, col2 = st.columns([1, 5])
with col1:
    try:
        st.image(LOGO_PATH, width=120)
    except FileNotFoundError:
        st.markdown("### 📊")

with col2:
    st.title(APP_TITLE)
    st.subheader(APP_SUBTITLE)

if df is None:
    st.info("👆 Utilisez la barre latérale pour charger un fichier et commencer l'analyse.")
    st.stop()

# Onglets principaux
tab1, tab2, tab3, tab4 = st.tabs(["📊 Tableau de bord", "🔍 Analyses", "🤖 Machine Learning", "📄 Exportations"])

with tab1:
    from pages.dashboard import main as dashboard_main
    dashboard_main(df)

with tab2:
    from pages.analyse import main as analyse_main
    analyse_main(df)

with tab3:
    from pages.ml import main as ml_main
    ml_main(df)

with tab4:
    from pages.export import main as export_main
    export_main(df)

# Footer
st.markdown("---")
st.caption("© 2025 Data Analytics Pro - Développé avec Streamlit ❤️")
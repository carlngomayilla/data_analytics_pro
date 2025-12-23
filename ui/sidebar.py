# ui/sidebar.py
import streamlit as st

def render():
    with st.sidebar:
        # Titre principal
        st.header("📁 Chargement des données")

        # File uploader avec zone de glissez-déposez visible et limite claire
        uploaded_file = st.file_uploader(
            "Uploader un fichier",
            type=['csv', 'xlsx', 'xls', 'parquet'],
            help="Formats supportés : CSV, Excel (.xlsx, .xls), Parquet | Limite : 200 Mo",
            label_visibility="collapsed"  # Cache le label pour plus de place à la zone de drop
        )

        # Affichage du nom du fichier chargé (feedback utilisateur)
        if uploaded_file is not None:
            st.success(f"✅ {uploaded_file.name} chargé")
            st.info(f"Taille : {uploaded_file.size / (1024*1024):.1f} Mo")

        st.markdown("---")

        # Section thème
        st.subheader("🎨 Thème")
        current_theme = st.session_state.get("theme", "dark")
        theme = st.radio(
            "Mode d'affichage",
            ["dark", "light"],
            index=0 if current_theme == "dark" else 1,
            label_visibility="collapsed"
        )
        if theme != current_theme:
            st.session_state["theme"] = theme
            st.rerun()  # Applique le thème immédiatement

        st.markdown("---")

        # Bouton de réinitialisation
        if st.button("🗑️ Réinitialiser les données", use_container_width=True):
            if 'df' in st.session_state:
                del st.session_state.df
            st.cache_data.clear()
            st.success("Données et cache réinitialisés")
            st.rerun()

        # Retour du fichier uploadé
        return uploaded_file
# ui/sidebar.py
import streamlit as st


def render():
    with st.sidebar:
        st.header("Chargement des donnees")

        uploaded_file = st.file_uploader(
            "Charger un fichier",
            type=["csv", "xlsx", "xls", "parquet"],
            help="Formats pris en charge: CSV, Excel (.xlsx, .xls), Parquet | Limite: 200 Mo",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            st.success(f"Fichier {uploaded_file.name} charge.")
            st.info(f"Taille: {uploaded_file.size / (1024 * 1024):.1f} Mo")

        st.markdown("---")

        st.subheader("Parametres d'affichage")
        current_theme = st.session_state.get("theme", "dark")
        theme = st.radio(
            "Mode d'affichage",
            ["dark", "light"],
            index=0 if current_theme == "dark" else 1,
            label_visibility="collapsed",
        )
        if theme != current_theme:
            st.session_state["theme"] = theme
            st.rerun()

        st.markdown("---")

        if st.button("Reinitialiser les donnees", use_container_width=True):
            if "df" in st.session_state:
                del st.session_state.df
            st.cache_data.clear()
            st.success("Les donnees et le cache ont ete reinitialises.")
            st.rerun()

        return uploaded_file


# ui/sidebar.py
import streamlit as st


# Explication: Affiche les controles de la barre laterale.
def render():
    with st.sidebar:
        st.header("Chargement des donnees")

        # Explication: Le fichier est valide uniquement quand l'utilisateur soumet le formulaire.
        uploaded_payload = st.session_state.get("uploaded_payload")
        upload_submitted = False
        with st.form("sidebar_upload_form"):
            uploaded_file = st.file_uploader(
                "Charger un fichier",
                type=["csv", "xlsx", "xls", "parquet"],
                help="Formats pris en charge: CSV, Excel (.xlsx, .xls), Parquet | Limite: 200 Mo",
                label_visibility="collapsed",
                key="sidebar_uploaded_file",
            )
            upload_submitted = st.form_submit_button("Charger le fichier")

        if upload_submitted:
            if uploaded_file is None:
                st.warning("Selectionnez un fichier avant de lancer le chargement.")
            else:
                uploaded_payload = {
                    "name": uploaded_file.name,
                    "size": int(uploaded_file.size),
                    "bytes": uploaded_file.getvalue(),
                }
                st.session_state.uploaded_payload = uploaded_payload

        if uploaded_payload is not None:
            st.success(f"Fichier actif: {uploaded_payload['name']}")
            st.info(f"Taille: {uploaded_payload['size'] / (1024 * 1024):.1f} Mo")

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

        if st.button("Reinitialiser les donnees", width="stretch"):
            st.session_state.clear()
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Les donnees et le cache ont ete reinitialises.")
            st.rerun()

        return uploaded_payload, upload_submitted




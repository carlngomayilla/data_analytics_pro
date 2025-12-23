# core/cache.py
import streamlit as st

@st.cache_data(show_spinner="Optimisation du cache...", ttl=3600)  # Cache 1 heure
def df_manager(df, key=None):
    if df is None:
        return None
    # Clé unique pour cache spécifique
    cache_key = key if key else "default_df"
    st.session_state[cache_key] = df.copy()
    return st.session_state[cache_key]

@st.cache_resource(show_spinner="Chargement des ressources...")
def resource_manager(obj):
    return obj
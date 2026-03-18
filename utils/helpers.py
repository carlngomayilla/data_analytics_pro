# utils/helpers.py
import streamlit as st

# Explication: Recupere une valeur de session, avec une valeur par defaut si absente.
def get_session_state(key, default=None):
    """
    Recupere ou initialise une valeur dans st.session_state de maniere securisee.
    """
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

# Fonction bonus utile pour les exports ou autres
# Explication: Formate un nombre pour un affichage plus lisible.
def format_number(num):
    if abs(num) >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif abs(num) >= 1_000:
        return f"{num / 1_000:.1f}K"
    return f"{num:.0f}"

# utils/helpers.py
import streamlit as st

def get_session_state(key, default=None):
    """
    Récupère ou initialise une valeur dans st.session_state de manière sécurisée
    """
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

# Fonction bonus utile pour les exports ou autres
def format_number(num):
    if abs(num) >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif abs(num) >= 1_000:
        return f"{num / 1_000:.1f}K"
    return f"{num:.0f}"
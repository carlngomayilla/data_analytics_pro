# pages/ml.py
import streamlit as st

def main(df):
    st.title("🤖 Machine Learning")

    if df is None:
        st.info("Chargez des données pour commencer.")
        return

    st.write("Fonctionnalités ML en cours de développement...")
    st.info("Bientôt : clustering K-Means, régression, classification")
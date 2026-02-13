# pages/ml.py
import streamlit as st


def main(df):
    st.title("Module Machine Learning")

    if df is None:
        st.info("Chargez des donnees pour commencer.")
        return

    st.write("Les fonctionnalites de Machine Learning sont en cours de developpement.")
    st.info("Fonctionnalites prevues: clustering K-Means, regression et classification.")


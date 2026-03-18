# core/data_cleaner.py
import streamlit as st


# Explication: Nettoie les donnees de base (valeurs manquantes, doublons, etc.).
def clean_data(df):
    original_shape = df.shape
    df = df.drop_duplicates()
    df = df.dropna(axis=1, how="all")
    df = df.fillna(0)
    st.info(f"Nettoyage: {original_shape[0] - df.shape[0]} doublons supprimes")
    return df



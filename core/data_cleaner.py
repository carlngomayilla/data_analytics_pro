# core/data_cleaner.py
import pandas as pd
import streamlit as st

def clean_data(df):
    original_shape = df.shape
    df = df.drop_duplicates()
    df = df.dropna(axis=1, how='all')  # Supprimer colonnes vides
    df = df.fillna(0)  # Remplir NaN par 0 (adaptable)
    st.info(f"Nettoyage : {original_shape[0] - df.shape[0]} doublons supprimés")
    return df
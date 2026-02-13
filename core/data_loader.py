# core/data_loader.py
import os

import pandas as pd
import streamlit as st


def load_data(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        os.makedirs("uploaded_data", exist_ok=True)
        save_path = os.path.join("uploaded_data", uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        name = uploaded_file.name.lower()
        if name.endswith(".csv"):
            df = pd.read_csv(save_path)
        elif name.endswith((".xls", ".xlsx")):
            df = pd.read_excel(save_path)
        elif name.endswith(".parquet"):
            df = pd.read_parquet(save_path)
        else:
            st.error("Format non pris en charge.")
            return None

        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement: {e}")
        return None


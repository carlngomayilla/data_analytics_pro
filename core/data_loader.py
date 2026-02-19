# core/data_loader.py
import os

import pandas as pd
import streamlit as st


def _read_csv_robust(csv_path: str) -> pd.DataFrame:
    attempts = [
        {"encoding": "utf-8-sig", "sep": None, "engine": "python"},
        {"encoding": "utf-8", "sep": None, "engine": "python"},
        {"encoding": "latin-1", "sep": None, "engine": "python"},
    ]
    last_error = None
    for options in attempts:
        try:
            return pd.read_csv(csv_path, low_memory=False, **options)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Lecture CSV impossible apres plusieurs tentatives: {last_error}")


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
            df = _read_csv_robust(save_path)
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



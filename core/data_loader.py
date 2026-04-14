from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st

from config.settings import UPLOAD_FOLDER


# Explication: Tente plusieurs encodages pour lire un CSV, meme si le fichier est mal encode.
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


# Explication: Charge un fichier utilisateur (CSV, Excel ou Parquet) et renvoie un DataFrame.
def load_data(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        name = Path(uploaded_file.name).name.lower()
        suffix = Path(name).suffix
        file_bytes = uploaded_file.getbuffer()

        temp_dir = Path(UPLOAD_FOLDER)
        temp_dir.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as temp_file:
            temp_file.write(file_bytes)
            temp_path = Path(temp_file.name)

        if name.endswith(".csv"):
            df = _read_csv_robust(str(temp_path))
        elif name.endswith((".xls", ".xlsx")):
            df = pd.read_excel(temp_path)
        elif name.endswith(".parquet"):
            df = pd.read_parquet(temp_path)
        else:
            st.error("Format non pris en charge.")
            return None

        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement: {e}")
        return None
    finally:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink(missing_ok=True)


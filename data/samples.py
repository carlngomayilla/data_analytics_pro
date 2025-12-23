# data/samples.py
import pandas as pd
import numpy as np

def load_sample(domain_name: str) -> pd.DataFrame:
    if domain_name == "Finance & Comptabilité":
        return pd.DataFrame({
            'Année': [2020, 2021, 2022, 2023, 2024],
            'Chiffre d’affaires (M€)': [150, 180, 210, 195, 230],
            'Résultat net (M€)': [12, 18, 25, 22, 30],
            'Total Actif (M€)': [200, 220, 250, 260, 280],
            'Capitaux propres (M€)': [100, 110, 130, 140, 160],
            'Dette financière (M€)': [80, 90, 100, 95, 100],
        })

    elif domain_name == "Général":
        dates = pd.date_range("2023-01-01", periods=150, freq='D')
        return pd.DataFrame({
            'Date': dates,
            'Ventes (€)': np.random.normal(1200, 400, 150).round(2),
            'Produit': np.random.choice(['Produit A', 'Produit B', 'Produit C'], 150),
            'Région': np.random.choice(['Nord', 'Sud', 'Est', 'Ouest'], 150),
            'Clients': np.random.randint(20, 300, 150),
            'Satisfaction': np.random.uniform(3.5, 5.0, 150).round(1)
        })

    return pd.DataFrame()
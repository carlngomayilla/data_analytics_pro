# pages/dashboard.py
import streamlit as st
import pandas as pd
import numpy as np

# === Fonction pour calculer l'indice de Gini ===
def gini_coefficient(x):
    """Calcule l'indice de Gini pour une série de valeurs numériques positives"""
    x = np.array(x.dropna())
    if len(x) == 0:
        return np.nan
    if np.any(x < 0):
        st.warning("L'indice de Gini est calculé sur des valeurs absolues (négatives ignorées).")
        x = np.abs(x)
    x = np.sort(x)
    n = len(x)
    cumx = np.cumsum(x)
    gini = (2 * np.sum((np.arange(1, n+1) * x)) / (n * cumx[-1])) - (n + 1) / n
    return round(gini, 4)

def main(df):
    st.title("📊 Tableau de bord – Statistiques descriptives et analytiques")

    if df is None or df.empty:
        st.info("Aucune donnée chargée. Utilisez la barre latérale pour uploader un fichier.")
        return

    # === 1. Statistiques descriptives numériques avec Gini ===
    st.header("1. Statistiques descriptives numériques (avec indice de Gini)")

    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    if numeric_cols:
        desc = df[numeric_cols].describe(percentiles=[.05, .1, .25, .5, .75, .9, .95]).T
        desc['mode'] = df[numeric_cols].mode().iloc[0]
        desc['skewness'] = df[numeric_cols].skew()
        desc['kurtosis'] = df[numeric_cols].kurtosis()
        desc['variance'] = df[numeric_cols].var()
        desc['cv (%)'] = (desc['std'] / desc['mean'] * 100).round(2)
        
        # Ajout de l'indice de Gini
        gini_values = [gini_coefficient(df[col]) for col in numeric_cols]
        desc['Gini'] = gini_values
        
        desc = desc.round(3)
        st.dataframe(desc, use_container_width=True)
        
        st.info("**Indice de Gini** : 0 = égalité parfaite, 1 = inégalité maximale. Très utilisé pour mesurer la concentration (revenus, ventes, etc.).")
    else:
        st.info("Aucune colonne numérique détectée.")

    # === 2. Statistiques de fréquence et répartition ===
    st.header("2. Statistiques de fréquence et répartition")

    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    if categorical_cols:
        for col in categorical_cols:
            with st.expander(f"Répartition de {col}"):
                freq = df[col].value_counts().head(20)
                freq_rel = df[col].value_counts(normalize=True).head(20) * 100
                table = pd.DataFrame({
                    "Valeur": freq.index.astype(str),
                    "Fréquence absolue": freq.values,
                    "Fréquence relative (%)": freq_rel.values.round(2)
                })
                st.dataframe(table, use_container_width=True)
    else:
        st.info("Aucune colonne catégorielle détectée.")

    # === 3. Qualité des données ===
    st.header("3. Statistiques de qualité des données")

    missing = df.isna().sum()
    missing_pct = (missing / len(df)) * 100
    quality = pd.DataFrame({
        "Colonne": df.columns,
        "Valeurs manquantes": missing.values,
        "Taux manquant (%)": missing_pct.round(2).values,
        "Doublons totaux": [df.duplicated().sum()] * len(df.columns)
    })
    st.dataframe(quality, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Taux global de valeurs manquantes", f"{missing_pct.mean():.2f}%")
    col2.metric("Nombre de lignes dupliquées", df.duplicated().sum())
    col3.metric("Complétude moyenne", f"{(1 - missing_pct.mean()/100)*100:.2f}%")

    # === 4. Statistiques bivariées (corrélations) ===
    st.header("4. Statistiques bivariées (corrélations)")

    if len(numeric_cols) >= 2:
        corr_pearson = df[numeric_cols].corr(method='pearson')
        corr_spearman = df[numeric_cols].corr(method='spearman')
        st.subheader("Corrélation de Pearson")
        st.dataframe(corr_pearson.round(3), use_container_width=True)
        st.subheader("Corrélation de Spearman")
        st.dataframe(corr_spearman.round(3), use_container_width=True)
    else:
        st.info("Pas assez de colonnes numériques pour les corrélations.")

    # === 5. Statistiques temporelles ===
    st.header("5. Statistiques temporelles")

    date_cols = df.select_dtypes(include='datetime64[ns]').columns.tolist()
    if date_cols:
        date_col = date_cols[0]
        st.write(f"Analyse temporelle sur **{date_col}**")
        df_sorted = df.sort_values(date_col).dropna(subset=[date_col])
        duration_days = (df_sorted[date_col].max() - df_sorted[date_col].min()).days
        st.metric("Durée totale (jours)", duration_days)
        st.metric("Nombre de dates uniques", df_sorted[date_col].dt.date.nunique())
    else:
        st.info("Aucune colonne de type date détectée.")

    # === 6. KPI et indicateurs globaux ===
    st.header("6. Indicateurs clés (KPI)")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Observations totales", len(df))
    col2.metric("Variables", len(df.columns))
    col3.metric("Taux de complétude moyen", f"{(1 - df.isna().mean().mean()) * 100:.2f}%")
    col4.metric("Densité de données", f"{(df.notna().sum().sum() / (len(df) * len(df.columns))) * 100:.2f}%")

    st.success("Toutes les statistiques descriptives et analytiques sont disponibles sous forme tabulaire.")
# pages/analyse.py
import streamlit as st
import pandas as pd
from core.visualization import (
    plot_distribution, plot_box, plot_violin, plot_density,
    plot_bar, plot_pie, plot_donut, plot_scatter,
    plot_line_evolution, plot_correlation_heatmap, plot_pairplot,
    plot_parallel_coordinates, plot_radar_chart, plot_gauge_chart, plot_waterfall_chart
)

# === Interprétations automatiques ===
def interpret_distribution(df, col):
    data = df[col].dropna()
    if data.empty or not pd.api.types.is_numeric_dtype(data):
        st.markdown("### 💡 Interprétation")
        st.info("Distribution non calculable (colonne non numérique ou vide).")
        return
    skew = data.skew()
    kurt = data.kurtosis()
    st.markdown("### 💡 Interprétation de la distribution")
    if abs(skew) < 0.5:
        st.success("Distribution symétrique")
    elif skew > 0.5:
        st.warning("Asymétrie à droite (queue positive)")
    else:
        st.warning("Asymétrie à gauche (queue négative)")

def interpret_boxplot(df, col):
    data = df[col].dropna()
    if data.empty or not pd.api.types.is_numeric_dtype(data):
        return
    q1 = data.quantile(0.25)
    q3 = data.quantile(0.75)
    iqr = q3 - q1
    outliers = ((data < q1 - 1.5*iqr) | (data > q3 + 1.5*iqr)).sum()
    st.markdown("### 💡 Interprétation du boxplot")
    st.info(f"50% des données entre {q1:.2f} et {q3:.2f}")
    if outliers > 0:
        st.warning(f"{outliers} outliers détectés")

def interpret_scatter(df, x, y):
    data = df[[x, y]].dropna()
    if data.empty or len(data) < 2:
        return
    corr = data.corr().iloc[0,1]
    strength = "forte" if abs(corr) > 0.7 else "modérée" if abs(corr) > 0.3 else "faible"
    direction = "positive" if corr > 0 else "négative" if corr < 0 else "aucune"
    st.markdown("### 💡 Interprétation du nuage de points")
    st.success(f"Corrélation {strength} {direction} (r = {corr:.3f})")

def main(df):
    st.title("🔍 Analyses Exploratoires Avancées")

    if df is None or df.empty:
        st.info("Chargez des données via la barre latérale pour commencer.")
        return

    # Thème actuel
    dark_mode = st.session_state.get("theme", "dark") == "dark"

    # Types de colonnes
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    all_cols = df.columns.tolist()

    # Filtrage dynamique
    st.sidebar.header("🔧 Filtres dynamiques")
    filtered_df = df.copy()

    for col in numeric_cols:
        if st.sidebar.checkbox(f"Filtrer {col}"):
            min_val = float(df[col].min())
            max_val = float(df[col].max())
            range_val = st.sidebar.slider(f"{col}", min_val, max_val, (min_val, max_val))
            filtered_df = filtered_df[(filtered_df[col] >= range_val[0]) & (filtered_df[col] <= range_val[1])]

    for col in categorical_cols:
        if st.sidebar.checkbox(f"Filtrer {col}"):
            selected = st.sidebar.multiselect(f"Valeurs {col}", df[col].unique(), default=df[col].unique())
            filtered_df = filtered_df[filtered_df[col].isin(selected)]

    st.sidebar.success(f"{len(filtered_df):,} lignes après filtrage")

    # Colonnes après filtrage
    numeric_cols_f = filtered_df.select_dtypes(include='number').columns.tolist()
    categorical_cols_f = filtered_df.select_dtypes(include=['object', 'category']).columns.tolist()
    all_cols_f = filtered_df.columns.tolist()

    # Onglets
    tab_uni, tab_bi, tab_multi = st.tabs(["Univariée", "Bivariée", "Multivariée"])

    with tab_uni:
        st.subheader("Analyse univariée")
        col = st.selectbox("Choisissez une colonne", all_cols_f, key="uni_col")
        plot_distribution(filtered_df, col, dark_mode=dark_mode)
        interpret_distribution(filtered_df, col)
        plot_box(filtered_df, col, dark_mode=dark_mode)
        interpret_boxplot(filtered_df, col)
        plot_violin(filtered_df, col, dark_mode=dark_mode)
        plot_density(filtered_df, col, dark_mode=dark_mode)
        if col in categorical_cols_f:
            plot_bar(filtered_df, col, dark_mode=dark_mode)
            plot_pie(filtered_df, col, dark_mode=dark_mode)
            plot_donut(filtered_df, col, dark_mode=dark_mode)

    with tab_bi:
        st.subheader("Analyse bivariée")
        x = st.selectbox("Axe X", all_cols_f, key="bi_x")
        y = st.selectbox("Axe Y", numeric_cols_f, key="bi_y")
        color = st.selectbox("Colorer par", ["Aucun"] + categorical_cols_f, key="bi_color")
        color = None if color == "Aucun" else color
        size = st.selectbox("Taille bulles par", ["Aucun"] + numeric_cols_f, key="bi_size")
        size = None if size == "Aucun" else size

        plot_scatter(filtered_df, x, y, color_col=color, size_col=size, dark_mode=dark_mode)
        interpret_scatter(filtered_df, x, y)
        plot_line_evolution(filtered_df, x, y, dark_mode=dark_mode)

    with tab_multi:
        st.subheader("Analyse multivariée – Relations entre plusieurs variables")

        # Heatmap de corrélation (toujours visible)
        plot_correlation_heatmap(filtered_df, dark_mode=dark_mode)

        # Pairplot (lourd – sur bouton)
        if len(numeric_cols_f) >= 3:
            if st.button("Générer Pairplot complet (scatter matrix)"):
                with st.spinner("Génération du pairplot en cours..."):
                    plot_pairplot(filtered_df, dark_mode=dark_mode)
        else:
            st.info("Au moins 3 colonnes numériques nécessaires pour le pairplot.")

        # Coordonnées parallèles
        if len(numeric_cols_f) >= 4:
            if st.button("Générer Coordonnées parallèles"):
                plot_parallel_coordinates(filtered_df, dark_mode=dark_mode)
        else:
            st.info("Au moins 4 colonnes numériques nécessaires pour les coordonnées parallèles.")

        # Radar chart (comparaison multi-critères)
        if len(numeric_cols_f) >= 3:
            st.write("**Radar chart – Comparaison de profils**")
            radar_cols = st.multiselect("Sélectionnez les critères (3 à 8)", numeric_cols_f, default=numeric_cols_f[:5])
            if len(radar_cols) >= 3 and len(radar_cols) <= 8:
                sample_profiles = filtered_df.sample(min(5, len(filtered_df)))  # 5 profils max pour lisibilité
                plot_radar_chart(sample_profiles, radar_cols, radar_cols, dark_mode=dark_mode)
            elif len(radar_cols) > 8:
                st.warning("Maximum 8 critères pour le radar (lisibilité).")
        else:
            st.info("Au moins 3 colonnes numériques nécessaires pour le radar.")

        # Gauge (KPI exemple)
        st.write("**Gauge – Suivi d’objectif**")
        gauge_value = st.slider("Valeur actuelle de l’objectif (%)", 0, 100, 75)
        plot_gauge_chart(gauge_value, "Taux d'atteinte objectif", dark_mode=dark_mode)

        # Waterfall exemple
        if st.checkbox("Afficher exemple Waterfall (contribution)"):
            # Exemple simple
            waterfall_data = pd.DataFrame({
                "label": ["Début", "+Ventes", "-Coûts", "+Marketing", "-Taxes", "Total"],
                "value": [100, 50, -30, 20, -15, 125]
            })
            plot_waterfall_chart(waterfall_data["value"], waterfall_data["label"], dark_mode=dark_mode)

        # Statistiques descriptives finales
        st.subheader("Statistiques descriptives globales")
        st.dataframe(filtered_df.describe(include='all'), use_container_width=True)

        st.subheader("Aperçu des données filtrées")
        st.dataframe(filtered_df.head(20), use_container_width=True)
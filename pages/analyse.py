# pages/analyse.py
import pandas as pd
import streamlit as st

from core.visualization import (
    plot_bar,
    plot_box,
    plot_correlation_heatmap,
    plot_density,
    plot_donut,
    plot_gauge_chart,
    plot_line_evolution,
    plot_pairplot,
    plot_parallel_coordinates,
    plot_pie,
    plot_radar_chart,
    plot_scatter,
    plot_violin,
    plot_waterfall_chart,
    plot_distribution,
)


# Interpretations automatiques
def safe_dataframe_display(df):
    try:
        st.dataframe(df, use_container_width=True)
    except OverflowError:
        st.warning(
            "Certaines valeurs sont trop grandes pour l'affichage natif. "
            "Conversion en texte appliquee."
        )
        st.dataframe(df.astype(str), use_container_width=True)


def interpret_distribution(df, col):
    data = df[col].dropna()
    if data.empty or not pd.api.types.is_numeric_dtype(data):
        st.markdown("### Interpretation")
        st.info("Distribution non calculable (colonne non numerique ou vide).")
        return

    skew = data.skew()
    st.markdown("### Interpretation de la distribution")
    if abs(skew) < 0.5:
        st.success("Distribution globalement symetrique.")
    elif skew > 0.5:
        st.warning("Asymetrie a droite (queue positive).")
    else:
        st.warning("Asymetrie a gauche (queue negative).")


def interpret_boxplot(df, col):
    data = df[col].dropna()
    if data.empty or not pd.api.types.is_numeric_dtype(data):
        return

    q1 = data.quantile(0.25)
    q3 = data.quantile(0.75)
    iqr = q3 - q1
    outliers = ((data < q1 - 1.5 * iqr) | (data > q3 + 1.5 * iqr)).sum()

    st.markdown("### Interpretation du boxplot")
    st.info(f"50 % des donnees se situent entre {q1:.2f} et {q3:.2f}.")
    if outliers > 0:
        st.warning(f"{outliers} valeurs atypiques detectees.")


def interpret_scatter(df, x, y):
    data = df[[x, y]].dropna()
    if data.empty or len(data) < 2:
        return

    x_num = pd.to_numeric(data[x], errors="coerce")
    y_num = pd.to_numeric(data[y], errors="coerce")
    valid = x_num.notna() & y_num.notna()
    if valid.sum() < 2:
        st.markdown("### Interpretation du nuage de points")
        st.info("Correlation non calculable: l'axe X contient des valeurs non numeriques.")
        return

    corr = x_num[valid].corr(y_num[valid])
    if pd.isna(corr):
        st.markdown("### Interpretation du nuage de points")
        st.info("Correlation non calculable sur les donnees selectionnees.")
        return

    strength = "forte" if abs(corr) > 0.7 else "moderee" if abs(corr) > 0.3 else "faible"
    direction = "positive" if corr > 0 else "negative" if corr < 0 else "nulle"
    st.markdown("### Interpretation du nuage de points")
    st.success(f"Correlation {strength} {direction} (r = {corr:.3f}).")


def main(df):
    st.title("Analyses exploratoires avancees")

    if df is None or df.empty:
        st.info("Chargez des donnees via la barre laterale pour commencer.")
        return

    dark_mode = st.session_state.get("theme", "dark") == "dark"

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    all_cols = df.columns.tolist()

    st.sidebar.header("Filtres dynamiques")
    filtered_df = df.copy()

    for col in numeric_cols:
        if st.sidebar.checkbox(f"Filtrer {col}"):
            min_val = float(df[col].min())
            max_val = float(df[col].max())
            range_val = st.sidebar.slider(f"{col}", min_val, max_val, (min_val, max_val))
            filtered_df = filtered_df[
                (filtered_df[col] >= range_val[0]) & (filtered_df[col] <= range_val[1])
            ]

    for col in categorical_cols:
        if st.sidebar.checkbox(f"Filtrer {col}"):
            selected = st.sidebar.multiselect(
                f"Valeurs {col}",
                df[col].unique(),
                default=df[col].unique(),
            )
            filtered_df = filtered_df[filtered_df[col].isin(selected)]

    st.sidebar.success(f"{len(filtered_df):,} lignes apres filtrage")

    numeric_cols_f = filtered_df.select_dtypes(include="number").columns.tolist()
    categorical_cols_f = filtered_df.select_dtypes(include=["object", "category"]).columns.tolist()
    all_cols_f = filtered_df.columns.tolist()

    tab_uni, tab_bi, tab_multi = st.tabs(
        [
            "Analyse univariee",
            "Analyse bivariee",
            "Analyse multivariee",
        ]
    )

    with tab_uni:
        st.subheader("Analyse univariee")
        col = st.selectbox("Selectionnez une colonne", all_cols_f, key="uni_col")
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
        st.subheader("Analyse bivariee")
        x = st.selectbox("Axe X", all_cols_f, key="bi_x")
        y = st.selectbox("Axe Y", numeric_cols_f, key="bi_y")
        color = st.selectbox("Colorer par", ["Aucun"] + categorical_cols_f, key="bi_color")
        color = None if color == "Aucun" else color
        size = st.selectbox("Dimension des bulles", ["Aucun"] + numeric_cols_f, key="bi_size")
        size = None if size == "Aucun" else size

        plot_scatter(filtered_df, x, y, color_col=color, size_col=size, dark_mode=dark_mode)
        interpret_scatter(filtered_df, x, y)
        plot_line_evolution(filtered_df, x, y, dark_mode=dark_mode)

    with tab_multi:
        st.subheader("Analyse multivariee - Relations entre variables")

        plot_correlation_heatmap(filtered_df, dark_mode=dark_mode)

        if len(numeric_cols_f) >= 3:
            if st.button("Generer la matrice de dispersion complete"):
                with st.spinner("Generation de la matrice de dispersion..."):
                    plot_pairplot(filtered_df, dark_mode=dark_mode)
        else:
            st.info("Au moins 3 colonnes numeriques sont necessaires pour la matrice de dispersion.")

        if len(numeric_cols_f) >= 4:
            if st.button("Generer le graphique en coordonnees paralleles"):
                plot_parallel_coordinates(filtered_df, dark_mode=dark_mode)
        else:
            st.info("Au moins 4 colonnes numeriques sont necessaires pour ce graphique.")

        if len(numeric_cols_f) >= 3:
            st.write("**Comparaison de profils (radar)**")
            radar_cols = st.multiselect(
                "Selectionnez les criteres (3 a 8)",
                numeric_cols_f,
                default=numeric_cols_f[:5],
            )
            if 3 <= len(radar_cols) <= 8:
                sample_profiles = filtered_df.sample(min(5, len(filtered_df)))
                plot_radar_chart(sample_profiles, radar_cols, radar_cols, dark_mode=dark_mode)
            elif len(radar_cols) > 8:
                st.warning("Le radar est limite a 8 criteres pour conserver la lisibilite.")
        else:
            st.info("Au moins 3 colonnes numeriques sont necessaires pour le radar.")

        st.write("**Suivi d'objectif (jauge)**")
        gauge_value = st.slider("Valeur actuelle de l'objectif (%)", 0, 100, 75)
        plot_gauge_chart(gauge_value, "Taux d'atteinte de l'objectif", dark_mode=dark_mode)

        if st.checkbox("Afficher un exemple de graphique en cascade"):
            waterfall_data = pd.DataFrame(
                {
                    "label": ["Depart", "+Ventes", "-Couts", "+Marketing", "-Taxes", "Total"],
                    "value": [100, 50, -30, 20, -15, 125],
                }
            )
            plot_waterfall_chart(waterfall_data["value"], waterfall_data["label"], dark_mode=dark_mode)



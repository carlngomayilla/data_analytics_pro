# core/visualization.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import numpy as np
import scipy.stats as stats
import pandas as pd

# === Layout dynamique clair/sombre ===
def get_layout(dark_mode: bool = False):
    if dark_mode:
        return dict(
            paper_bgcolor="#0e1117",
            plot_bgcolor="#262730",
            font=dict(color="#fafafa"),
            title_font=dict(color="#fafafa"),
            template="plotly_dark"
        )
    else:
        return dict(
            paper_bgcolor="white",
            plot_bgcolor="#f8f9fa",
            font=dict(color="#000000"),
            title_font=dict(color="#000000"),
            template="plotly_white"
        )

# === Key unique robuste ===
if not hasattr(st.session_state, "plot_counter"):
    st.session_state.plot_counter = 0

def get_unique_key(base: str):
    st.session_state.plot_counter += 1
    return f"{base}_{st.session_state.plot_counter}"

# === Graphiques univariés ===
def plot_distribution(df, column, dark_mode=False):
    if column not in df.columns:
        st.warning("Colonne non trouvée.")
        return
    data = df[column].dropna()
    if data.empty:
        st.info("Aucune donnée valide.")
        return
    title = f"Distribution de {column}"
    fig = px.histogram(
        data,
        x=column,
        nbins=50,
        marginal="violin",
        histnorm='probability density',
        title=title,
        color_discrete_sequence=['#636EFA'] if not dark_mode else ['#8b5cf6'],
        opacity=0.7
    )
    fig.update_layout(bargap=0.1, height=600, **get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key(f"dist_{column}"))

def plot_box(df, column, by=None, dark_mode=False):
    if column not in df.columns:
        return
    title = f"Box Plot de {column}" + (f" par {by}" if by else "")
    fig = px.box(df, y=column, x=by, color=by, points="outliers", title=title)
    fig.update_layout(height=600, **get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key(f"box_{column}_{by or 'none'}"))

def plot_violin(df, column, by=None, dark_mode=False):
    title = f"Violin Plot de {column}" + (f" par {by}" if by else "")
    fig = px.violin(df, y=column, x=by, color=by, box=True, points="all", title=title)
    fig.update_layout(height=600, **get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key(f"violin_{column}_{by or 'none'}"))

def plot_density(df, column, dark_mode=False):
    if column not in df.columns:
        st.warning("Colonne non trouvée.")
        return
    data = df[column].dropna()
    if data.empty or not pd.api.types.is_numeric_dtype(data):
        st.info("La densité est disponible uniquement pour les colonnes numériques.")
        return
    title = f"Densité de {column}"
    fig = ff.create_distplot([data], [column], show_hist=False, show_rug=False)
    fig.update_layout(title=title, height=500, **get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key(f"density_{column}"))

def plot_bar(df, column, top_n=15, dark_mode=False):
    if column not in df.columns:
        return
    counts = df[column].value_counts().head(top_n)
    title = f"Top {top_n} de {column}"
    fig = px.bar(x=counts.index, y=counts.values, title=title,
                 labels={'x': column, 'y': 'Fréquence'},
                 color=counts.values, color_continuous_scale='Viridis' if not dark_mode else 'plasma')
    fig.update_layout(height=600, **get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key(f"bar_{column}"))

def plot_pie(df, column, dark_mode=False):
    if column not in df.columns:
        return
    counts = df[column].value_counts()
    title = f"Répartition de {column}"
    fig = px.pie(counts, values=counts.values, names=counts.index, title=title)
    fig.update_layout(**get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key(f"pie_{column}"))

def plot_donut(df, column, dark_mode=False):
    if column not in df.columns:
        return
    counts = df[column].value_counts()
    title = f"Répartition de {column}"
    fig = px.pie(counts, values=counts.values, names=counts.index, hole=0.4, title=title)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(**get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key(f"donut_{column}"))

def plot_scatter(df, x_col, y_col, color_col=None, size_col=None, dark_mode=False):
    title = f"{y_col} en fonction de {x_col}"

    # Colonnes réellement disponibles
    available_cols = set(df.columns)

    # Colonnes hover sécurisées
    hover_cols = [c for c in [x_col, y_col, color_col, size_col] if c and c in available_cols]

    # Colonnes nécessaires au graphique
    plot_cols = set(hover_cols)

    # Nettoyage size_col
    if size_col and size_col in available_cols:
        size_data = df[size_col].dropna()
        if size_data.empty:
            size_clean = pd.Series(10, index=df.index)
        else:
            size_clean = df[size_col].fillna(size_data.mean()).clip(lower=1)
        df = df.copy()
        df["size_clean"] = size_clean
        size_col = "size_clean"
        plot_cols.add("size_clean")
    else:
        size_col = None

    # Sécurisation color_col
    if color_col not in available_cols:
        color_col = None

    # DataFrame final pour Plotly
    data = df[list(plot_cols)].copy()

    fig = px.scatter(
        data_frame=data,
        x=x_col,
        y=y_col,
        color=color_col,
        size=size_col,
        hover_data=hover_cols,
        title=title,
        opacity=0.7
    )

    line_color = "white" if dark_mode else "DarkSlateGrey"
    fig.update_traces(marker=dict(line=dict(width=1, color=line_color)))
    fig.update_layout(height=600, **get_layout(dark_mode))

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=get_unique_key(
            f"scatter_{x_col}_{y_col}_{color_col or 'none'}_{size_col or 'none'}"
        )
    )

# === Graphiques multivariés ===
def plot_correlation_heatmap(df, dark_mode=False):
    numeric_df = df.select_dtypes(include='number')
    if len(numeric_df.columns) < 2:
        st.info("Pas assez de colonnes numériques pour la corrélation.")
        return
    corr = numeric_df.corr()
    fig = px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale='RdBu_r',
        title="Matrice de corrélation",
        height=600
    )
    fig.update_layout(**get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key("corr_heatmap"))

def plot_pairplot(df, dark_mode=False):
    numeric_df = df.select_dtypes(include='number')
    if len(numeric_df.columns) < 2:
        st.info("Pas assez de colonnes numériques.")
        return
    fig = px.scatter_matrix(
        numeric_df,
        dimensions=numeric_df.columns,
        color=numeric_df.columns[0],
        title="Pairplot des variables numériques",
        height=800
    )
    fig.update_layout(**get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key("pairplot"))

# === Fonctions ajoutées pour l'onglet Multivariée ===
def plot_parallel_coordinates(df, dark_mode=False):
    numeric_df = df.select_dtypes(include='number')
    if len(numeric_df.columns) < 2:
        st.info("Pas assez de colonnes numériques.")
        return
    fig = px.parallel_coordinates(
        numeric_df,
        color=numeric_df.columns[0],
        title="Coordonnées parallèles"
    )
    fig.update_layout(**get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key("parallel_coordinates"))

def plot_radar_chart(df, categories, values, dark_mode=False):
    fig = go.Figure()
    for i in range(len(df)):
        fig.add_trace(go.Scatterpolar(
            r=df.iloc[i][values].values,
            theta=categories,
            fill='toself',
            name=df.index[i] if df.index.name else f"Profil {i+1}"
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=True,
        title="Radar chart – Comparaison de profils",
        **get_layout(dark_mode)
    )
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key("radar_chart"))

def plot_gauge_chart(value, title, dark_mode=False):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta={'reference': 100},
        title={'text': title},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue" if not dark_mode else "cyan"}
        }
    ))
    fig.update_layout(height=500, **get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key("gauge_chart"))

def plot_waterfall_chart(values, labels, dark_mode=False):
    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=["relative"] * (len(values)-1) + ["total"],
        x=labels,
        y=values,
        textposition="outside",
        text=values
    ))
    fig.update_layout(title="Waterfall – Contribution", **get_layout(dark_mode))
    st.plotly_chart(fig, use_container_width=True, key=get_unique_key("waterfall_chart"))


def plot_line_evolution(df, x_col, y_col, dark_mode=False):
    # Vérifications de sécurité
    if x_col not in df.columns or y_col not in df.columns:
        st.warning("Colonnes sélectionnées invalides.")
        return

    data = df[[x_col, y_col]].dropna()

    if data.empty:
        st.info("Aucune donnée disponible pour l’évolution temporelle.")
        return

    template = "plotly_dark" if dark_mode else "plotly_white"

    fig = px.line(
        data,
        x=x_col,
        y=y_col,
        markers=True,
        title=f"Évolution de {y_col} en fonction de {x_col}",
        template=template
    )

    fig.update_layout(
        xaxis_title=x_col,
        yaxis_title=y_col,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)


__all__ = [
    "plot_distribution",
    "plot_box",
    "plot_correlation_heatmap",
    "plot_scatter",
    "plot_line_evolution",
    "plot_bar",
    "plot_pie",
    "plot_pairplot"
]

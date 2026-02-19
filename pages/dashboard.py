# pages/dashboard.py
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st


INT64_MIN = np.iinfo(np.int64).min
INT64_MAX = np.iinfo(np.int64).max


def _normalize_bigints_for_arrow(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convertit les entiers Python hors int64 en texte pour eviter les erreurs Arrow."""
    safe_df = dataframe.copy()
    object_cols = safe_df.select_dtypes(include=["object"]).columns

    for col in object_cols:
        has_out_of_range_int = safe_df[col].map(
            lambda value: isinstance(value, int) and not (INT64_MIN <= value <= INT64_MAX)
        ).any()
        if has_out_of_range_int:
            safe_df[col] = safe_df[col].astype(str)

    return safe_df


def safe_dataframe_display(dataframe: pd.DataFrame) -> None:
    try:
        st.dataframe(_normalize_bigints_for_arrow(dataframe), width="stretch")
    except OverflowError:
        st.warning(
            "Certaines valeurs sont trop grandes pour l'affichage natif. "
            "Conversion en texte appliquee."
        )
        st.dataframe(dataframe.astype(str), width="stretch")


def _safe_export_name(name: str, fallback: str = "tableau") -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(name))
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    cleaned = cleaned.strip("_")
    return cleaned if cleaned else fallback


def _prepare_export_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    export_df = dataframe.copy()
    if not isinstance(export_df.index, pd.RangeIndex) or export_df.index.name is not None:
        index_name = export_df.index.name or "index"
        export_df = export_df.reset_index().rename(columns={"index": index_name})
    return _normalize_bigints_for_arrow(export_df)


def _to_excel_bytes(dataframe: pd.DataFrame, sheet_name: str = "tableau") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    output.seek(0)
    return output.getvalue()


def render_exportable_table(
    dataframe: pd.DataFrame,
    export_key: str,
    file_stem: str,
    sheet_name: str,
) -> None:
    safe_dataframe_display(dataframe)

    export_df = _prepare_export_dataframe(dataframe)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
    xlsx_bytes = _to_excel_bytes(export_df, sheet_name=sheet_name)

    st.caption("Exporter ce tableau")
    col_csv, col_xlsx = st.columns(2)
    col_csv.download_button(
        "Exporter CSV",
        data=csv_bytes,
        file_name=f"{file_stem}.csv",
        mime="text/csv",
        key=f"{export_key}_csv",
        width="stretch",
    )
    col_xlsx.download_button(
        "Exporter Excel",
        data=xlsx_bytes,
        file_name=f"{file_stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"{export_key}_xlsx",
        width="stretch",
    )


def gini_coefficient(x):
    """Calcule l'indice de Gini pour une serie de valeurs numeriques positives."""
    x = np.array(x.dropna())
    if len(x) == 0:
        return np.nan

    if np.any(x < 0):
        st.warning("L'indice de Gini est calcule sur des valeurs absolues (valeurs negatives ignorees).")
        x = np.abs(x)

    x = np.sort(x)
    n = len(x)
    cumx = np.cumsum(x)
    gini = (2 * np.sum((np.arange(1, n + 1) * x)) / (n * cumx[-1])) - (n + 1) / n
    return round(gini, 4)


def main(df):
    st.title("Tableau de bord - Statistiques descriptives et analytiques")

    if df is None or df.empty:
        st.info("Aucune donnee chargee. Utilisez la barre laterale pour importer un fichier.")
        return

    st.header("1. Statistiques descriptives numeriques (incluant l'indice de Gini)")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        desc = df[numeric_cols].describe(percentiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]).T
        desc["mode"] = df[numeric_cols].mode().iloc[0]
        desc["skewness"] = df[numeric_cols].skew()
        desc["kurtosis"] = df[numeric_cols].kurtosis()
        desc["variance"] = df[numeric_cols].var()
        desc["cv (%)"] = (desc["std"] / desc["mean"] * 100).round(2)
        desc["Gini"] = [gini_coefficient(df[col]) for col in numeric_cols]
        desc = desc.round(3)
        render_exportable_table(
            dataframe=desc,
            export_key="dashboard_stats_numeriques",
            file_stem="dashboard_stats_numeriques",
            sheet_name="stats_numeriques",
        )

        st.info(
            "Indice de Gini: 0 = egalite parfaite, 1 = inegalite maximale. "
            "Cet indicateur mesure la concentration (revenus, ventes, etc.)."
        )
    else:
        st.info("Aucune colonne numerique detectee.")

    st.header("2. Statistiques de frequence et de repartition")

    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if categorical_cols:
        for idx, col in enumerate(categorical_cols):
            with st.expander(f"Repartition de {col}"):
                freq = df[col].value_counts().head(20)
                freq_rel = df[col].value_counts(normalize=True).head(20) * 100
                table = pd.DataFrame(
                    {
                        "Valeur": freq.index.astype(str),
                        "Frequence absolue": freq.values,
                        "Frequence relative (%)": freq_rel.values.round(2),
                    }
                )
                col_slug = _safe_export_name(col, fallback=f"colonne_{idx + 1}")
                render_exportable_table(
                    dataframe=table,
                    export_key=f"dashboard_repartition_{idx}_{col_slug}",
                    file_stem=f"dashboard_repartition_{col_slug}",
                    sheet_name=f"rep_{col_slug}",
                )
    else:
        st.info("Aucune colonne categorielle detectee.")

    st.header("3. Qualite des donnees")

    missing = df.isna().sum()
    missing_pct = (missing / len(df)) * 100
    quality = pd.DataFrame(
        {
            "Colonne": df.columns,
            "Valeurs manquantes": missing.values,
            "Taux manquant (%)": missing_pct.round(2).values,
            "Doublons totaux": [df.duplicated().sum()] * len(df.columns),
        }
    )
    render_exportable_table(
        dataframe=quality,
        export_key="dashboard_qualite_donnees",
        file_stem="dashboard_qualite_donnees",
        sheet_name="qualite_donnees",
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Taux global de valeurs manquantes", f"{missing_pct.mean():.2f}%")
    col2.metric("Nombre de lignes dupliquees", df.duplicated().sum())
    col3.metric("Completude moyenne", f"{(1 - missing_pct.mean() / 100) * 100:.2f}%")

    st.header("4. Statistiques bivariees (correlations)")

    if len(numeric_cols) >= 2:
        corr_pearson = df[numeric_cols].corr(method="pearson")
        corr_spearman = df[numeric_cols].corr(method="spearman")
        st.subheader("Correlation de Pearson")
        render_exportable_table(
            dataframe=corr_pearson.round(3),
            export_key="dashboard_corr_pearson",
            file_stem="dashboard_correlation_pearson",
            sheet_name="corr_pearson",
        )
        st.subheader("Correlation de Spearman")
        render_exportable_table(
            dataframe=corr_spearman.round(3),
            export_key="dashboard_corr_spearman",
            file_stem="dashboard_correlation_spearman",
            sheet_name="corr_spearman",
        )
    else:
        st.info("Pas assez de colonnes numeriques pour les correlations.")

    st.header("5. Statistiques temporelles")

    date_cols = df.select_dtypes(include="datetime64[ns]").columns.tolist()
    if date_cols:
        date_col = date_cols[0]
        st.write(f"Analyse temporelle sur **{date_col}**")
        df_sorted = df.sort_values(date_col).dropna(subset=[date_col])
        duration_days = (df_sorted[date_col].max() - df_sorted[date_col].min()).days
        st.metric("Duree totale (jours)", duration_days)
        st.metric("Nombre de dates uniques", df_sorted[date_col].dt.date.nunique())
    else:
        st.info("Aucune colonne de type date detectee.")

    st.header("6. Indicateurs cles (KPI)")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Observations totales", len(df))
    col2.metric("Variables", len(df.columns))
    col3.metric("Taux de completude moyen", f"{(1 - df.isna().mean().mean()) * 100:.2f}%")
    col4.metric(
        "Densite des donnees",
        f"{(df.notna().sum().sum() / (len(df) * len(df.columns))) * 100:.2f}%",
    )

    st.header("7. Statistiques descriptives globales et apercu des donnees")

    st.subheader("Statistiques descriptives globales")
    global_desc = df.describe(include="all")
    render_exportable_table(
        dataframe=global_desc,
        export_key="dashboard_stats_globales",
        file_stem="dashboard_stats_globales",
        sheet_name="stats_globales",
    )

    st.subheader("Apercu des donnees")
    preview_df = df.head(20)
    render_exportable_table(
        dataframe=preview_df,
        export_key="dashboard_apercu_donnees",
        file_stem="dashboard_apercu_donnees",
        sheet_name="apercu_donnees",
    )

    st.success("Les statistiques descriptives et analytiques sont disponibles sous forme tabulaire.")




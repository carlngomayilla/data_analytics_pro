import pandas as pd
import streamlit as st


def _compare_as_text(
    series: pd.Series,
    query: str,
    search_mode: str,
    case_sensitive: bool,
) -> pd.Series:
    values = series.fillna("").astype(str)
    target = query if case_sensitive else query.lower()

    if not case_sensitive:
        values = values.str.lower()

    if search_mode == "Egal":
        return values.eq(target)

    return values.str.contains(target, regex=False, na=False)


def _build_search_mask(
    df: pd.DataFrame,
    selected_column: str,
    query: str,
    search_mode: str,
    case_sensitive: bool,
) -> pd.Series:
    if selected_column == "Toutes les colonnes":
        mask = pd.Series(False, index=df.index)
        for column in df.columns:
            mask = mask | _compare_as_text(df[column], query, search_mode, case_sensitive)
        return mask

    series = df[selected_column]
    if search_mode == "Egal" and pd.api.types.is_numeric_dtype(series):
        numeric_query = pd.to_numeric(query, errors="coerce")
        if pd.notna(numeric_query):
            return series.eq(numeric_query)

    return _compare_as_text(series, query, search_mode, case_sensitive)


def _restore_types(updated_df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
    restored = updated_df.copy()

    numeric_cols = reference_df.select_dtypes(include="number").columns.tolist()
    for col in numeric_cols:
        restored[col] = pd.to_numeric(restored[col], errors="coerce")

    datetime_cols = reference_df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()
    for col in datetime_cols:
        restored[col] = pd.to_datetime(restored[col], errors="coerce")

    return restored


def main(df: pd.DataFrame) -> None:
    st.title("Recherche et modification de donnees")

    if df is None or df.empty:
        st.info("Chargez un fichier pour utiliser la recherche et l'edition.")
        return

    if "active_editor_version" not in st.session_state:
        st.session_state.active_editor_version = 1

    st.caption(f"Base active: {len(df):,} lignes x {len(df.columns)} colonnes.")

    selected_column = st.selectbox("Colonne a explorer", ["Toutes les colonnes"] + df.columns.tolist())
    search_mode = st.radio("Type de recherche", ["Contient", "Egal"], horizontal=True)
    case_sensitive = st.checkbox("Respecter la casse", value=False)
    query = st.text_input("Valeur a rechercher")

    if not query.strip():
        st.info("Saisissez une valeur pour lancer la recherche.")
        return

    mask = _build_search_mask(df, selected_column, query.strip(), search_mode, case_sensitive)
    matching_df = df.loc[mask].copy()

    st.metric("Lignes trouvees", len(matching_df))

    if matching_df.empty:
        st.warning("Aucune ligne ne correspond a votre recherche.")
        return

    max_rows = min(2000, len(matching_df))
    default_rows = min(200, max_rows)
    rows_to_edit = st.slider(
        "Nombre de lignes a afficher et modifier",
        min_value=1,
        max_value=max_rows,
        value=default_rows,
        step=1,
    )

    editable_df = matching_df.head(rows_to_edit).copy()
    editor_key = f"active_editor_{st.session_state.active_editor_version}"
    edited_df = st.data_editor(editable_df, use_container_width=True, key=editor_key)

    if st.button("Enregistrer les modifications dans la base active"):
        updated_df = st.session_state.df.copy()
        common_index = edited_df.index.intersection(updated_df.index)
        updated_df.loc[common_index, edited_df.columns] = edited_df.loc[common_index, edited_df.columns]
        st.session_state.df = _restore_types(updated_df, df)

        # Force la reconstruction de la base de nettoyage si ce module est ensuite utilise.
        st.session_state.pop("cleaning_df", None)
        st.session_state.pop("cleaning_source_signature", None)

        st.session_state.active_editor_version += 1
        st.success("Les modifications ont ete enregistrees dans la base active.")
        st.rerun()

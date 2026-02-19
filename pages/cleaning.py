import os
import re
from io import BytesIO

import pandas as pd
import streamlit as st


def _normalize_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    text_cols = normalized.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in text_cols:
        normalized[col] = normalized[col].replace(r"^\s*$", pd.NA, regex=True)
    return normalized


def _source_signature(df: pd.DataFrame) -> tuple:
    return (
        len(df),
        tuple(df.columns.tolist()),
        tuple(str(dtype) for dtype in df.dtypes.tolist()),
    )


def _safe_filename(name: str, fallback: str = "base_nettoyee") -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "").strip())
    safe = safe.strip("_")
    return safe if safe else fallback


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="data_nettoyee")
    output.seek(0)
    return output.getvalue()


def _reset_working_df_if_needed(df: pd.DataFrame) -> None:
    signature = _source_signature(df)
    if st.session_state.get("cleaning_source_signature") != signature:
        st.session_state.cleaning_source_signature = signature
        st.session_state.cleaning_df = _normalize_missing_values(df)
        st.session_state.cleaning_editor_version = st.session_state.get("cleaning_editor_version", 0) + 1


def _bump_editor_version() -> None:
    st.session_state.cleaning_editor_version = st.session_state.get("cleaning_editor_version", 0) + 1


def _missing_mask(df: pd.DataFrame) -> pd.DataFrame:
    return df.isna()


def _restore_numeric_types(df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
    restored = df.copy()
    numeric_cols = reference_df.select_dtypes(include="number").columns.tolist()
    for col in numeric_cols:
        restored[col] = pd.to_numeric(restored[col], errors="coerce")
    return restored


def main(df: pd.DataFrame) -> None:
    st.title("Preparation et nettoyage des donnees")

    if df is None or df.empty:
        st.info("Chargez un fichier pour utiliser le module de nettoyage.")
        return

    _reset_working_df_if_needed(df)
    working_df = st.session_state.cleaning_df

    missing = _missing_mask(working_df)
    missing_per_row = missing.sum(axis=1)
    row_with_missing_count = int((missing_per_row > 0).sum())
    fully_empty_rows_count = int((missing_per_row == working_df.shape[1]).sum())
    missing_cells_count = int(missing.sum().sum())

    col1, col2, col3 = st.columns(3)
    col1.metric("Lignes avec valeurs manquantes", row_with_missing_count)
    col2.metric("Lignes totalement vides", fully_empty_rows_count)
    col3.metric("Cellules manquantes", missing_cells_count)

    st.subheader("Repartition des valeurs manquantes par ligne")
    grouped = (
        missing_per_row[missing_per_row > 0]
        .value_counts()
        .sort_index()
        .rename_axis("Nombre de cellules vides par ligne")
        .reset_index(name="Nombre de lignes")
    )
    if grouped.empty:
        st.success("Aucune valeur manquante detectee.")
    else:
        st.dataframe(grouped, width="stretch")

    if fully_empty_rows_count > 0:
        if st.button("Supprimer les lignes totalement vides"):
            st.session_state.cleaning_df = working_df.loc[missing_per_row < working_df.shape[1]].copy()
            _bump_editor_version()
            st.success(f"{fully_empty_rows_count} lignes totalement vides ont ete supprimees.")
            st.rerun()

    st.subheader("Correction automatique par mediane")
    numeric_cols = working_df.select_dtypes(include="number").columns.tolist()
    numeric_missing_cols = [col for col in numeric_cols if working_df[col].isna().any()]
    selected_cols = st.multiselect(
        "Colonnes numeriques a corriger par mediane",
        numeric_missing_cols,
        default=numeric_missing_cols,
    )

    if st.button("Appliquer la correction automatique"):
        if not selected_cols:
            st.warning("Selectionnez au moins une colonne.")
        else:
            updated = working_df.copy()
            total_filled = 0
            skipped_cols = []
            for col in selected_cols:
                before = int(updated[col].isna().sum())
                median = updated[col].median()
                if pd.isna(median):
                    skipped_cols.append(col)
                    continue
                updated[col] = updated[col].fillna(median)
                after = int(updated[col].isna().sum())
                total_filled += before - after

            st.session_state.cleaning_df = updated
            _bump_editor_version()
            message = f"{total_filled} valeurs ont ete remplacees par la mediane."
            if skipped_cols:
                message += " Colonnes ignorees (mediane indisponible): " + ", ".join(skipped_cols)
            st.success(message)
            st.rerun()

    st.subheader("Correction manuelle")
    show_only_missing = st.checkbox("Afficher uniquement les lignes avec valeurs manquantes", value=True)
    max_rows = st.slider("Nombre maximal de lignes editables", min_value=20, max_value=2000, value=300, step=20)

    if show_only_missing:
        editable_df = working_df.loc[missing_per_row > 0].copy()
    else:
        editable_df = working_df.copy()

    editable_df = editable_df.head(max_rows)
    editor_key = f"cleaning_editor_{st.session_state.get('cleaning_editor_version', 1)}"
    edited_df = st.data_editor(editable_df, width="stretch", key=editor_key)

    if st.button("Enregistrer les modifications manuelles"):
        updated = working_df.copy()
        common_index = edited_df.index.intersection(updated.index)
        updated.loc[common_index, edited_df.columns] = edited_df.loc[common_index, edited_df.columns]
        updated = _normalize_missing_values(updated)
        updated = _restore_numeric_types(updated, df)
        st.session_state.cleaning_df = updated
        _bump_editor_version()
        st.success("Les modifications manuelles ont ete enregistrees.")
        st.rerun()

    st.subheader("Validation et export de la base nettoyee")
    filename_base = st.text_input("Nom du fichier", value="base_nettoyee")
    safe_name = _safe_filename(filename_base)

    if st.button("Utiliser cette base comme base active"):
        st.session_state.df = st.session_state.cleaning_df.copy()
        st.success("La base nettoyee est desormais la base active de l'application.")

    save_format = st.selectbox("Format de sauvegarde locale", ["csv", "xlsx"], index=0)
    if st.button("Enregistrer dans le projet"):
        os.makedirs("data", exist_ok=True)
        if save_format == "csv":
            save_path = os.path.join("data", f"{safe_name}.csv")
            st.session_state.cleaning_df.to_csv(save_path, index=False, encoding="utf-8-sig")
        else:
            save_path = os.path.join("data", f"{safe_name}.xlsx")
            with pd.ExcelWriter(save_path, engine="openpyxl") as writer:
                st.session_state.cleaning_df.to_excel(writer, index=False, sheet_name="data_nettoyee")
        st.success(f"Base enregistree: {save_path}")

    csv_bytes = st.session_state.cleaning_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    excel_bytes = _to_excel_bytes(st.session_state.cleaning_df)

    export_col1, export_col2 = st.columns(2)
    with export_col1:
        st.download_button(
            "Telecharger en CSV",
            data=csv_bytes,
            file_name=f"{safe_name}.csv",
            mime="text/csv",
        )
    with export_col2:
        st.download_button(
            "Telecharger en Excel",
            data=excel_bytes,
            file_name=f"{safe_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )




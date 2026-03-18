import warnings
from datetime import date, datetime
from io import BytesIO

import pandas as pd
import streamlit as st


# Explication: Recupere une colonne en serie pandas, ou une serie vide si absente.
def _as_series(df: pd.DataFrame, col: str) -> pd.Series:
    selected = df.loc[:, col]
    if isinstance(selected, pd.DataFrame):
        return selected.iloc[:, 0]
    return selected


# Explication: Compare deux colonnes comme texte pour une recherche souple.
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


# Explication: Construit un masque booleen pour la recherche multicritere.
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
            mask = mask | _compare_as_text(_as_series(df, column), query, search_mode, case_sensitive)
        return mask

    series = _as_series(df, selected_column)
    if search_mode == "Egal" and pd.api.types.is_numeric_dtype(series):
        numeric_query = pd.to_numeric(query, errors="coerce")
        if pd.notna(numeric_query):
            return pd.to_numeric(series, errors="coerce").eq(numeric_query)

    return _compare_as_text(series, query, search_mode, case_sensitive)


# Explication: Calcule le masque de recherche avec cache pour eviter les recalculs inutiles.
@st.cache_data(show_spinner=False)
def _cached_build_search_mask(
    df: pd.DataFrame,
    selected_column: str,
    query: str,
    search_mode: str,
    case_sensitive: bool,
) -> pd.Series:
    return _build_search_mask(df, selected_column, query, search_mode, case_sensitive)


# Explication: Convertit une serie en dates/heures de maniere robuste.
def _to_datetime_series(series: pd.Series) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        parsed = pd.to_datetime(series, errors="coerce")

    if isinstance(parsed, pd.Series):
        tz_info = getattr(parsed.dtype, "tz", None)
        if tz_info is not None:
            return parsed.dt.tz_localize(None)
        if pd.api.types.is_datetime64_any_dtype(parsed):
            return parsed
    if isinstance(parsed, pd.DatetimeIndex):
        if parsed.tz is not None:
            parsed = parsed.tz_localize(None)
        return pd.Series(parsed, index=series.index)

    # Explication: Convertit une valeur texte vers un type exploitable (date, nombre, etc.).
    def _parse_value(value):
        if pd.isna(value):
            return pd.NaT
        try:
            ts = pd.Timestamp(value)
        except Exception:
            return pd.NaT
        if ts.tzinfo is not None:
            ts = ts.tz_localize(None)
        return ts

    return series.map(_parse_value)


# Explication: Detecte si une colonne ressemble a des dates.
def _looks_like_datetime(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    non_null = series.dropna()
    if non_null.empty:
        return False

    parsed = _to_datetime_series(non_null)
    return bool((parsed.notna().mean()) >= 0.8)


# Explication: Applique un filtre de texte sur une colonne.
def _apply_text_filter(
    series: pd.Series,
    operator: str,
    value: str,
    case_sensitive: bool,
) -> pd.Series:
    raw_values = series.astype("string")
    empty_mask = series.isna() | raw_values.fillna("").str.strip().eq("")

    if operator == "Vide":
        return empty_mask
    if operator == "Non vide":
        return ~empty_mask

    values = raw_values.fillna("")
    target = value if case_sensitive else value.lower()

    if not case_sensitive:
        values = values.str.lower()

    if operator == "Egal":
        return values.eq(target)
    if operator == "Different":
        return ~values.eq(target)
    if operator == "Commence par":
        return values.str.startswith(target, na=False)
    if operator == "Finit par":
        return values.str.endswith(target, na=False)

    return values.str.contains(target, regex=False, na=False)


# Explication: Applique un filtre numerique (intervalle, seuil, etc.).
def _apply_numeric_filter(
    series: pd.Series,
    operator: str,
    value1: float | None,
    value2: float | None = None,
) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")

    if operator == "Vide":
        return values.isna()
    if operator == "Non vide":
        return values.notna()
    if value1 is None:
        return pd.Series(False, index=series.index)

    if operator == "=":
        return values.eq(value1)
    if operator == "!=":
        return values.ne(value1)
    if operator == ">":
        return values.gt(value1)
    if operator == ">=":
        return values.ge(value1)
    if operator == "<":
        return values.lt(value1)
    if operator == "<=":
        return values.le(value1)
    if operator == "Entre":
        if value2 is None:
            return pd.Series(False, index=series.index)
        low = min(value1, value2)
        high = max(value1, value2)
        return values.between(low, high, inclusive="both")

    return pd.Series(False, index=series.index)


# Explication: Applique un filtre sur une plage de dates.
def _apply_datetime_filter(
    series: pd.Series,
    operator: str,
    value1,
    value2=None,
) -> pd.Series:
    values = _to_datetime_series(series).dt.normalize()

    if operator == "Vide":
        return values.isna()
    if operator == "Non vide":
        return values.notna()
    if value1 is None:
        return pd.Series(False, index=series.index)

    ts1 = pd.Timestamp(value1).normalize()

    if operator == "=":
        return values.eq(ts1)
    if operator == "!=":
        return values.ne(ts1)
    if operator == ">":
        return values.gt(ts1)
    if operator == ">=":
        return values.ge(ts1)
    if operator == "<":
        return values.lt(ts1)
    if operator == "<=":
        return values.le(ts1)
    if operator == "Entre":
        if value2 is None:
            return pd.Series(False, index=series.index)
        ts2 = pd.Timestamp(value2).normalize()
        low = min(ts1, ts2)
        high = max(ts1, ts2)
        return values.between(low, high, inclusive="both")

    return pd.Series(False, index=series.index)


# Explication: Combine plusieurs masques de filtre (ET/OU).
def _combine_masks(masks: list[pd.Series], mode: str, index) -> pd.Series:
    if not masks:
        return pd.Series(True, index=index)

    if mode == "OU":
        combined = pd.Series(False, index=index)
        for mask in masks:
            combined = combined | mask.fillna(False)
        return combined

    combined = pd.Series(True, index=index)
    for mask in masks:
        combined = combined & mask.fillna(False)
    return combined


# Explication: Affiche les filtres croises et renvoie le resultat filtre.
def _render_cross_filters(
    df: pd.DataFrame,
    case_sensitive: bool,
    key_prefix: str = "cross_filter",
) -> tuple[pd.Series, int]:
    st.subheader("Filtres croises")
    combine_mode = st.radio(
        "Combinaison des filtres croises",
        ["ET", "OU"],
        horizontal=True,
        key=f"{key_prefix}_combine",
    )
    filter_count = st.slider(
        "Nombre de filtres croises",
        min_value=1,
        max_value=8,
        value=2,
        key=f"{key_prefix}_count",
    )

    masks: list[pd.Series] = []
    active_filters = 0

    for idx in range(filter_count):
        with st.expander(f"Filtre {idx + 1}", expanded=idx == 0):
            is_active = st.checkbox(
                "Activer ce filtre",
                value=False,
                key=f"{key_prefix}_active_{idx}",
            )

            selected_column = st.selectbox(
                "Colonne",
                options=df.columns.tolist(),
                key=f"{key_prefix}_col_{idx}",
            )

            if not is_active:
                st.caption("Filtre inactif")
                continue

            series = _as_series(df, selected_column)
            is_numeric = pd.api.types.is_numeric_dtype(series)
            is_datetime = _looks_like_datetime(series)

            if is_numeric:
                st.caption("Type detecte: numerique")
                operator = st.selectbox(
                    "Operateur",
                    ["=", "!=", ">", ">=", "<", "<=", "Entre", "Vide", "Non vide"],
                    key=f"{key_prefix}_op_{idx}",
                )
                if operator == "Entre":
                    col_min, col_max = st.columns(2)
                    min_val = col_min.number_input(
                        "Valeur min",
                        key=f"{key_prefix}_num_min_{idx}",
                        value=0.0,
                        format="%.6f",
                    )
                    max_val = col_max.number_input(
                        "Valeur max",
                        key=f"{key_prefix}_num_max_{idx}",
                        value=0.0,
                        format="%.6f",
                    )
                    mask = _apply_numeric_filter(series, operator, float(min_val), float(max_val))
                elif operator in {"Vide", "Non vide"}:
                    mask = _apply_numeric_filter(series, operator, None, None)
                else:
                    value = st.number_input(
                        "Valeur",
                        key=f"{key_prefix}_num_val_{idx}",
                        value=0.0,
                        format="%.6f",
                    )
                    mask = _apply_numeric_filter(series, operator, float(value), None)

            elif is_datetime:
                st.caption("Type detecte: date")
                operator = st.selectbox(
                    "Operateur",
                    ["=", "!=", ">", ">=", "<", "<=", "Entre", "Vide", "Non vide"],
                    key=f"{key_prefix}_op_{idx}",
                )

                parsed_dates = _to_datetime_series(series)
                valid_dates = parsed_dates.dropna()
                if valid_dates.empty and operator not in {"Vide", "Non vide"}:
                    st.warning("Aucune date exploitable dans cette colonne. Filtre ignore.")
                    continue

                if valid_dates.empty:
                    default_start = date.today()
                    default_end = date.today()
                else:
                    default_start = valid_dates.min().date()
                    default_end = valid_dates.max().date()

                if operator == "Entre":
                    col_start, col_end = st.columns(2)
                    start_date = col_start.date_input(
                        "Date debut",
                        value=default_start,
                        min_value=default_start,
                        max_value=default_end,
                        key=f"{key_prefix}_date_start_{idx}",
                    )
                    end_date = col_end.date_input(
                        "Date fin",
                        value=default_end,
                        min_value=default_start,
                        max_value=default_end,
                        key=f"{key_prefix}_date_end_{idx}",
                    )
                    mask = _apply_datetime_filter(series, operator, start_date, end_date)
                elif operator in {"Vide", "Non vide"}:
                    mask = _apply_datetime_filter(series, operator, None, None)
                else:
                    selected_date = st.date_input(
                        "Date",
                        value=default_start,
                        min_value=default_start,
                        max_value=default_end,
                        key=f"{key_prefix}_date_val_{idx}",
                    )
                    mask = _apply_datetime_filter(series, operator, selected_date, None)

            else:
                st.caption("Type detecte: texte")
                operator = st.selectbox(
                    "Operateur",
                    ["Contient", "Egal", "Different", "Commence par", "Finit par", "Vide", "Non vide"],
                    key=f"{key_prefix}_op_{idx}",
                )

                if operator in {"Vide", "Non vide"}:
                    mask = _apply_text_filter(series, operator, "", case_sensitive)
                else:
                    value = st.text_input("Valeur", key=f"{key_prefix}_txt_val_{idx}")
                    if not value.strip():
                        st.caption("Filtre ignore: renseignez une valeur.")
                        continue
                    mask = _apply_text_filter(series, operator, value.strip(), case_sensitive)

            masks.append(mask.fillna(False))
            active_filters += 1

    combined_mask = _combine_masks(masks, combine_mode, df.index)
    return combined_mask, active_filters


# Explication: Restaure les types de colonnes apres edition.
def _restore_types(updated_df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
    restored = updated_df.copy()

    numeric_cols = reference_df.select_dtypes(include="number").columns.tolist()
    for col in numeric_cols:
        restored[col] = pd.to_numeric(restored[col], errors="coerce")

    datetime_cols = reference_df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()
    for col in datetime_cols:
        restored[col] = pd.to_datetime(restored[col], errors="coerce")

    return restored


# Explication: Convertit un tableau en fichier Excel en memoire (bytes).
def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="ResultatsRecherche", index=False)
    output.seek(0)
    return output.getvalue()


# Explication: Cree une signature de la source pour detecter les changements de donnees.
def _source_signature(df: pd.DataFrame) -> tuple:
    return (
        len(df),
        tuple(df.columns.tolist()),
        tuple(str(dtype) for dtype in df.dtypes.tolist()),
    )


# Explication: Initialise l'historique d'edition si necessaire.
def _init_edit_history_if_needed(df: pd.DataFrame) -> None:
    signature = _source_signature(df)
    if st.session_state.get("data_editor_source_signature") != signature:
        st.session_state.data_editor_source_signature = signature
        st.session_state.data_editor_undo_stack = []
        st.session_state.data_editor_redo_stack = []
        st.session_state.data_editor_change_log = []
        st.session_state.data_editor_matching_index = df.index.tolist()
        st.session_state.data_editor_last_search_meta = {
            "has_query": False,
            "active_cross_filters": 0,
            "last_run_at": None,
        }

    if "data_editor_undo_stack" not in st.session_state:
        st.session_state.data_editor_undo_stack = []
    if "data_editor_redo_stack" not in st.session_state:
        st.session_state.data_editor_redo_stack = []
    if "data_editor_change_log" not in st.session_state:
        st.session_state.data_editor_change_log = []
    if "data_editor_matching_index" not in st.session_state:
        st.session_state.data_editor_matching_index = df.index.tolist()
    if "data_editor_last_search_meta" not in st.session_state:
        st.session_state.data_editor_last_search_meta = {
            "has_query": False,
            "active_cross_filters": 0,
            "last_run_at": None,
        }


# Explication: Compte les lignes, colonnes et cellules modifiees.
def _count_changed_cells(before_df: pd.DataFrame, after_df: pd.DataFrame) -> tuple[int, int, int]:
    common_index = before_df.index.intersection(after_df.index)
    common_cols = before_df.columns.intersection(after_df.columns)
    if len(common_index) == 0 or len(common_cols) == 0:
        return 0, 0, 0

    before_view = before_df.loc[common_index, common_cols]
    after_view = after_df.loc[common_index, common_cols]

    changed = before_view.ne(after_view) | (before_view.isna() ^ after_view.isna())
    changed_cells = int(changed.to_numpy().sum())
    changed_rows = int(changed.any(axis=1).sum())
    changed_cols = int(changed.any(axis=0).sum())
    return changed_cells, changed_rows, changed_cols


# Explication: Ajoute un etat precedent dans la pile d'annulation.
def _push_undo_snapshot(previous_df: pd.DataFrame, max_depth: int = 10) -> None:
    stack = st.session_state.get("data_editor_undo_stack", [])
    stack.append(previous_df.copy())
    if len(stack) > max_depth:
        stack = stack[-max_depth:]
    st.session_state.data_editor_undo_stack = stack


# Explication: Ajoute un etat precedent dans la pile de retablissement.
def _push_redo_snapshot(previous_df: pd.DataFrame, max_depth: int = 10) -> None:
    stack = st.session_state.get("data_editor_redo_stack", [])
    stack.append(previous_df.copy())
    if len(stack) > max_depth:
        stack = stack[-max_depth:]
    st.session_state.data_editor_redo_stack = stack


# Explication: Ajoute une entree dans le journal des modifications.
def _append_change_log(action: str, changed_rows: int, changed_cols: int, changed_cells: int) -> None:
    logs = st.session_state.get("data_editor_change_log", [])
    logs.append(
        {
            "Horodatage": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Action": action,
            "Lignes modifiees": changed_rows,
            "Colonnes modifiees": changed_cols,
            "Cellules modifiees": changed_cells,
        }
    )
    st.session_state.data_editor_change_log = logs[-50:]


# Explication: Affiche l'historique des modifications utilisateur.
def _render_edit_history(reference_df: pd.DataFrame) -> None:
    undo_stack = st.session_state.get("data_editor_undo_stack", [])
    redo_stack = st.session_state.get("data_editor_redo_stack", [])
    logs = st.session_state.get("data_editor_change_log", [])

    st.subheader("Historique des modifications")
    col_undo, col_redo, col_log = st.columns(3)
    with col_undo:
        if st.button("Annuler (Undo)", disabled=len(undo_stack) == 0, key="data_editor_undo"):
            current = st.session_state.df.copy()
            previous = undo_stack.pop()
            _push_redo_snapshot(current)
            st.session_state.data_editor_undo_stack = undo_stack
            st.session_state.df = _restore_types(previous, reference_df)
            st.session_state.active_editor_version += 1
            st.session_state.pop("cleaning_df", None)
            st.session_state.pop("cleaning_source_signature", None)
            _append_change_log("Undo", 0, 0, 0)
            st.success("Derniere modification annulee.")
            st.rerun()
    with col_redo:
        if st.button("Retablir (Redo)", disabled=len(redo_stack) == 0, key="data_editor_redo"):
            current = st.session_state.df.copy()
            next_df = redo_stack.pop()
            _push_undo_snapshot(current)
            st.session_state.data_editor_redo_stack = redo_stack
            st.session_state.df = _restore_types(next_df, reference_df)
            st.session_state.active_editor_version += 1
            st.session_state.pop("cleaning_df", None)
            st.session_state.pop("cleaning_source_signature", None)
            _append_change_log("Redo", 0, 0, 0)
            st.success("Modification retablie.")
            st.rerun()
    with col_log:
        st.metric("Actions en memoire", len(logs))

    with st.expander("Journal des modifications", expanded=False):
        if logs:
            st.dataframe(pd.DataFrame(logs[::-1]), width="stretch")
        else:
            st.caption("Aucune modification enregistree pour le moment.")


# Explication: Orchestre l'ecran: lit les entrees utilisateur puis affiche les resultats.
def main(df: pd.DataFrame) -> None:
    st.title("Recherche et modification de donnees")

    if df is None or df.empty:
        st.info("Chargez un fichier pour utiliser la recherche et l'edition.")
        return

    if "active_editor_version" not in st.session_state:
        st.session_state.active_editor_version = 1
    _init_edit_history_if_needed(st.session_state.get("df", df))

    st.caption(f"Base active: {len(df):,} lignes x {len(df.columns)} colonnes.")
    st.caption("Version recherche: export-filtrage v3 (2026-02-18)")
    _render_edit_history(st.session_state.get("df", df))

    st.subheader("Recherche simple")
    selected_column = st.selectbox(
        "Colonne a explorer",
        ["Toutes les colonnes"] + df.columns.tolist(),
        key="data_editor_selected_column",
    )
    search_mode = st.radio(
        "Type de recherche",
        ["Contient", "Egal"],
        horizontal=True,
        key="data_editor_search_mode",
    )
    case_sensitive = st.checkbox(
        "Respecter la casse",
        value=False,
        key="data_editor_case_sensitive",
    )
    query = st.text_input("Valeur a rechercher (optionnel)", key="data_editor_query")
    export_anchor = st.container()

    enable_cross_filters = st.checkbox(
        "Activer les filtres croises",
        value=False,
        key="data_editor_enable_cross_filters",
    )

    cross_mask = pd.Series(True, index=df.index)
    active_cross_filters = 0
    if enable_cross_filters:
        cross_mask, active_cross_filters = _render_cross_filters(df, case_sensitive)

    has_query = bool(query.strip())
    has_active_cross_filters = enable_cross_filters and active_cross_filters > 0
    if not has_query and not has_active_cross_filters:
        st.info("Aucun critere actif: export et edition appliques a toute la base.")

    final_mask = pd.Series(True, index=df.index)

    if has_query:
        simple_mask = _build_search_mask(df, selected_column, query.strip(), search_mode, case_sensitive)
        final_mask = final_mask & simple_mask.fillna(False)

    if has_active_cross_filters:
        final_mask = final_mask & cross_mask.fillna(False)

    matching_df = df.loc[final_mask].copy()

    st.metric("Lignes trouvees", len(matching_df))
    if enable_cross_filters:
        st.caption(f"Filtres croises actifs: {active_cross_filters}")

    with export_anchor:
        st.markdown("### Export du resultat du filtrage")
        st.caption("Utilisez ces boutons pour telecharger exactement les lignes affichees par les filtres ci-dessus.")
        export_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_col_csv, export_col_xlsx = st.columns(2)

        if matching_df.empty:
            st.warning("Aucune ligne ne correspond a votre recherche.")
            with export_col_csv:
                st.download_button(
                    "Exporter en CSV",
                    data=b"",
                    file_name=f"resultats_recherche_{export_timestamp}.csv",
                    mime="text/csv",
                    width="stretch",
                    disabled=True,
                    key="search_export_csv",
                )
            with export_col_xlsx:
                st.download_button(
                    "Exporter en Excel",
                    data=b"",
                    file_name=f"resultats_recherche_{export_timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                    disabled=True,
                    key="search_export_excel",
                )
            return

        export_csv = None
        export_csv_error = None
        try:
            export_csv = matching_df.to_csv(index=False).encode("utf-8-sig")
        except Exception as exc:
            export_csv_error = exc

        export_excel_error = None
        export_excel = None
        try:
            export_excel = _to_excel_bytes(matching_df)
        except Exception as exc:
            export_excel_error = exc

        with export_col_csv:
            st.download_button(
                "Exporter en CSV",
                data=export_csv if export_csv is not None else b"",
                file_name=f"resultats_recherche_{export_timestamp}.csv",
                mime="text/csv",
                width="stretch",
                disabled=export_csv is None,
                key="search_export_csv",
            )
        with export_col_xlsx:
            st.download_button(
                "Exporter en Excel",
                data=export_excel if export_excel is not None else b"",
                file_name=f"resultats_recherche_{export_timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
                disabled=export_excel is None,
                key="search_export_excel",
            )
        if export_csv_error is not None:
            st.caption(f"Export CSV indisponible: {export_csv_error}")
        if export_excel_error is not None:
            st.caption(f"Export Excel indisponible: {export_excel_error}")

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
    edited_df = st.data_editor(editable_df, width="stretch", key=editor_key)

    if st.button("Enregistrer les modifications dans la base active"):
        current_df = st.session_state.df.copy()
        updated_df = current_df.copy()
        common_index = edited_df.index.intersection(updated_df.index)
        updated_df.loc[common_index, edited_df.columns] = edited_df.loc[common_index, edited_df.columns]
        updated_df = _restore_types(updated_df, current_df)
        changed_cells, changed_rows, changed_cols = _count_changed_cells(current_df, updated_df)

        if changed_cells == 0:
            st.info("Aucune modification detectee a enregistrer.")
            return

        _push_undo_snapshot(current_df)
        st.session_state.data_editor_redo_stack = []
        _append_change_log("Edition", changed_rows, changed_cols, changed_cells)
        st.session_state.df = updated_df

        # Force la reconstruction de la base de nettoyage si ce module est ensuite utilise.
        st.session_state.pop("cleaning_df", None)
        st.session_state.pop("cleaning_source_signature", None)

        st.session_state.active_editor_version += 1
        st.success(
            f"Modifications enregistrees: {changed_cells} cellules, "
            f"{changed_rows} lignes, {changed_cols} colonnes."
        )
        st.rerun()


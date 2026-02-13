import re
from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st


def _dax_table_ref(table_name: str) -> str:
    safe_name = (table_name or "Data").strip().replace("'", "''")
    if not safe_name:
        safe_name = "Data"
    return f"'{safe_name}'"


def _dax_col_ref(table_name: str, column_name: str) -> str:
    return f"{_dax_table_ref(table_name)}[{column_name}]"


def _sanitize_measure_name(name: str, fallback: str = "Mesure") -> str:
    cleaned = "".join(ch for ch in (name or "") if ch.isalnum() or ch in " _-")
    cleaned = cleaned.strip()
    return cleaned if cleaned else fallback


def _safe_filename(name: str, fallback: str = "visual_dax") -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in (name or ""))
    cleaned = cleaned.strip("_")
    return cleaned if cleaned else fallback


def _measure_ref(name: str, fallback: str = "Mesure") -> str:
    return f"[{_sanitize_measure_name(name, fallback=fallback)}]"


def _build_basic_measure(table_name: str, column_name: str, metric_type: str, measure_name: str) -> str:
    col_ref = _dax_col_ref(table_name, column_name)
    expressions = {
        "Somme": f"SUM({col_ref})",
        "Moyenne": f"AVERAGE({col_ref})",
        "Minimum": f"MIN({col_ref})",
        "Maximum": f"MAX({col_ref})",
        "Nombre de valeurs": f"COUNT({col_ref})",
        "Nombre distinct": f"DISTINCTCOUNT({col_ref})",
    }
    expr = expressions[metric_type]
    return f"{_sanitize_measure_name(measure_name)} = {expr}"


def _build_ratio_measure(table_name: str, numerator_col: str, denominator_col: str, measure_name: str) -> str:
    numerator_ref = _dax_col_ref(table_name, numerator_col)
    denominator_ref = _dax_col_ref(table_name, denominator_col)
    return (
        f"{_sanitize_measure_name(measure_name)} = "
        f"DIVIDE(SUM({numerator_ref}), SUM({denominator_ref}), 0)"
    )


def _build_time_intelligence_block(
    table_name: str, value_col: str, date_col: str, base_measure_name: str
) -> list[str]:
    value_ref = _dax_col_ref(table_name, value_col)
    date_ref = _dax_col_ref(table_name, date_col)
    base_measure = _sanitize_measure_name(base_measure_name, fallback=f"Total {value_col}")

    return [
        f"{base_measure} = SUM({value_ref})",
        f"{base_measure} YTD = TOTALYTD([{base_measure}], {date_ref})",
        f"{base_measure} MTD = TOTALMTD([{base_measure}], {date_ref})",
        (
            f"{base_measure} M-1 = "
            f"CALCULATE([{base_measure}], DATEADD({date_ref}, -1, MONTH))"
        ),
        (
            f"Croissance M/M {base_measure} (%) = "
            f"DIVIDE([{base_measure}] - [{base_measure} M-1], [{base_measure} M-1], 0)"
        ),
    ]


def _build_context_block(table_name: str, value_measure_name: str, dimension_col: str) -> list[str]:
    table_ref = _dax_table_ref(table_name)
    dim_ref = _dax_col_ref(table_name, dimension_col)
    measure_name = _sanitize_measure_name(value_measure_name, fallback="Mesure Valeur")

    return [
        (
            f"% du total {measure_name} = "
            f"DIVIDE([{measure_name}], CALCULATE([{measure_name}], ALL({table_ref})), 0)"
        ),
        (
            f"Rang {dimension_col} par {measure_name} = "
            f"RANKX(ALL({dim_ref}), [{measure_name}], , DESC, DENSE)"
        ),
    ]


def _build_filter_measure(
    table_name: str,
    base_measure_name: str,
    filter_col: str,
    filter_value: str,
    measure_name: str,
) -> str:
    table_ref = _dax_table_ref(table_name)
    col_ref = _dax_col_ref(table_name, filter_col)
    safe_value = (filter_value or "").replace('"', '""')
    return (
        f"{_sanitize_measure_name(measure_name)} = "
        f"CALCULATE({_measure_ref(base_measure_name, fallback='Mesure Base')}, "
        f"FILTER({table_ref}, {col_ref} = \"{safe_value}\"))"
    )


def _build_removefilters_measure(
    table_name: str,
    base_measure_name: str,
    scope_col: str | None,
    measure_name: str,
) -> str:
    target = _dax_table_ref(table_name) if scope_col is None else _dax_col_ref(table_name, scope_col)
    return (
        f"{_sanitize_measure_name(measure_name)} = "
        f"CALCULATE({_measure_ref(base_measure_name, fallback='Mesure Base')}, REMOVEFILTERS({target}))"
    )


def _build_yoy_block(base_measure_name: str, date_ref: str) -> list[str]:
    base = _sanitize_measure_name(base_measure_name, fallback="Mesure Base")
    return [
        (
            f"{base} PY = "
            f"CALCULATE({_measure_ref(base)}, SAMEPERIODLASTYEAR({date_ref}))"
        ),
        f"Var {base} vs PY = {_measure_ref(base)} - {_measure_ref(f'{base} PY')}",
        (
            f"Var {base} vs PY pct = "
            f"DIVIDE({_measure_ref(f'Var {base} vs PY')}, {_measure_ref(f'{base} PY')}, 0)"
        ),
    ]


def _build_topn_measure(
    table_name: str,
    base_measure_name: str,
    dimension_col: str,
    top_n: int,
    measure_name: str,
) -> str:
    dim_ref = _dax_col_ref(table_name, dimension_col)
    return (
        f"{_sanitize_measure_name(measure_name)} = "
        f"CALCULATE({_measure_ref(base_measure_name, fallback='Mesure Base')}, "
        f"KEEPFILTERS(TOPN({top_n}, ALL({dim_ref}), {_measure_ref(base_measure_name, fallback='Mesure Base')}, DESC)))"
    )


def _store_snippet(formula: str) -> None:
    if "dax_snippets" not in st.session_state:
        st.session_state.dax_snippets = []
    st.session_state.dax_snippets.append(formula)


def _show_snippet(formula: str, button_key: str) -> None:
    st.code(formula, language="sql")
    if st.button("Ajouter la mesure au script DAX", key=button_key):
        _store_snippet(formula)
        st.success("La mesure a ete ajoutee au script DAX.")


def _first_formula_line(snippet: str) -> str:
    for line in (snippet or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _parse_supported_measure(formula_line: str) -> dict | None:
    if "=" not in (formula_line or ""):
        return None

    name_part, expr_part = formula_line.split("=", 1)
    measure_name = _sanitize_measure_name(name_part.strip(), fallback="Mesure")
    expr = expr_part.strip()

    agg_pattern = re.compile(
        r"^(SUM|AVERAGE|MIN|MAX|COUNT|DISTINCTCOUNT)\(\s*'[^']*(?:''[^']*)*'\[(?P<col>.+?)\]\s*\)\s*$",
        re.IGNORECASE,
    )
    ratio_pattern = re.compile(
        r"^DIVIDE\(\s*SUM\(\s*'[^']*(?:''[^']*)*'\[(?P<num>.+?)\]\s*\)\s*,\s*SUM\(\s*'[^']*(?:''[^']*)*'\[(?P<den>.+?)\]\s*\)\s*,\s*0\s*\)\s*$",
        re.IGNORECASE,
    )

    ratio_match = ratio_pattern.match(expr)
    if ratio_match:
        return {
            "measure_name": measure_name,
            "metric_type": "Ratio",
            "target_col": None,
            "numerator_col": ratio_match.group("num"),
            "denominator_col": ratio_match.group("den"),
            "formula": formula_line,
        }

    agg_match = agg_pattern.match(expr)
    if agg_match:
        function_name = agg_match.group(1).upper()
        metric_map = {
            "SUM": "Somme",
            "AVERAGE": "Moyenne",
            "MIN": "Minimum",
            "MAX": "Maximum",
            "COUNT": "Nombre de valeurs",
            "DISTINCTCOUNT": "Nombre distinct",
        }
        return {
            "measure_name": measure_name,
            "metric_type": metric_map[function_name],
            "target_col": agg_match.group("col"),
            "numerator_col": None,
            "denominator_col": None,
            "formula": formula_line,
        }

    return None


def _validate_metric_spec(
    df: pd.DataFrame,
    metric_type: str,
    target_col: str | None,
    numerator_col: str | None,
    denominator_col: str | None,
) -> str | None:
    if metric_type == "Ratio":
        if numerator_col not in df.columns or denominator_col not in df.columns:
            return "Les colonnes du ratio ne sont pas presentes dans la base chargee."
        return None

    if target_col not in df.columns:
        return "La colonne cible n'est pas presente dans la base chargee."

    return None


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _compute_metric_global(
    df: pd.DataFrame,
    metric_type: str,
    target_col: str | None,
    numerator_col: str | None,
    denominator_col: str | None,
) -> float:
    if metric_type == "Ratio":
        numerator = _to_numeric(df[numerator_col]).sum()
        denominator = _to_numeric(df[denominator_col]).sum()
        if pd.isna(denominator) or float(denominator) == 0.0:
            return 0.0
        return float(numerator / denominator)

    if metric_type == "Somme":
        return float(_to_numeric(df[target_col]).sum())
    if metric_type == "Moyenne":
        return float(_to_numeric(df[target_col]).mean())
    if metric_type == "Minimum":
        return float(_to_numeric(df[target_col]).min())
    if metric_type == "Maximum":
        return float(_to_numeric(df[target_col]).max())
    if metric_type == "Nombre de valeurs":
        return float(df[target_col].count())
    if metric_type == "Nombre distinct":
        return float(df[target_col].nunique(dropna=True))

    return float("nan")


def _compute_metric_by_dimension(
    df: pd.DataFrame,
    dimension_col: str,
    metric_type: str,
    measure_name: str,
    target_col: str | None,
    numerator_col: str | None,
    denominator_col: str | None,
) -> pd.DataFrame:
    if metric_type == "Ratio":
        working_df = df[[dimension_col, numerator_col, denominator_col]].copy()
        working_df[numerator_col] = _to_numeric(working_df[numerator_col])
        working_df[denominator_col] = _to_numeric(working_df[denominator_col])
        grouped = working_df.groupby(dimension_col, dropna=False)
        numerator = grouped[numerator_col].sum(min_count=1)
        denominator = grouped[denominator_col].sum(min_count=1)
        values = numerator / denominator.replace(0, pd.NA)
    else:
        working_df = df[[dimension_col, target_col]].copy()
        grouped = working_df.groupby(dimension_col, dropna=False)

        if metric_type == "Somme":
            working_df[target_col] = _to_numeric(working_df[target_col])
            grouped = working_df.groupby(dimension_col, dropna=False)
            values = grouped[target_col].sum(min_count=1)
        elif metric_type == "Moyenne":
            working_df[target_col] = _to_numeric(working_df[target_col])
            grouped = working_df.groupby(dimension_col, dropna=False)
            values = grouped[target_col].mean()
        elif metric_type == "Minimum":
            working_df[target_col] = _to_numeric(working_df[target_col])
            grouped = working_df.groupby(dimension_col, dropna=False)
            values = grouped[target_col].min()
        elif metric_type == "Maximum":
            working_df[target_col] = _to_numeric(working_df[target_col])
            grouped = working_df.groupby(dimension_col, dropna=False)
            values = grouped[target_col].max()
        elif metric_type == "Nombre de valeurs":
            values = grouped[target_col].count()
        elif metric_type == "Nombre distinct":
            values = grouped[target_col].nunique(dropna=True)
        else:
            values = pd.Series(dtype="float64")

    result = values.reset_index(name=measure_name)
    result[measure_name] = pd.to_numeric(result[measure_name], errors="coerce")

    raw_dim = result[dimension_col]
    result[dimension_col] = raw_dim.astype("string").fillna("(Vide)")
    return result


def _prepare_visual_dataframe(
    grouped_df: pd.DataFrame,
    dimension_col: str,
    measure_name: str,
    chart_type: str,
    top_n: int,
) -> pd.DataFrame:
    result = grouped_df.copy()
    if chart_type in {"Ligne", "Aire"}:
        parsed_dates = pd.to_datetime(result[dimension_col], errors="coerce")
        if parsed_dates.notna().any():
            result["_sort_date"] = parsed_dates
            result = result.sort_values("_sort_date", ascending=True).drop(columns=["_sort_date"])
        else:
            result = result.sort_values(dimension_col, ascending=True)
        return result.head(top_n)

    result = result.sort_values(measure_name, ascending=False)
    return result.head(top_n)


def _build_visual_figure(
    visual_df: pd.DataFrame,
    dimension_col: str,
    measure_name: str,
    chart_type: str,
):
    if visual_df.empty:
        return None

    if chart_type == "Barres":
        fig = px.bar(visual_df, x=dimension_col, y=measure_name, text_auto=".2f")
    elif chart_type == "Ligne":
        fig = px.line(visual_df, x=dimension_col, y=measure_name, markers=True)
    elif chart_type == "Aire":
        fig = px.area(visual_df, x=dimension_col, y=measure_name)
    elif chart_type == "Camembert":
        fig = px.pie(visual_df, names=dimension_col, values=measure_name)
    else:
        return None

    fig.update_layout(height=520, title=f"{measure_name} par {dimension_col}")
    return fig


def _to_excel_bytes(df: pd.DataFrame, sheet_name: str = "visual_dax") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    output.seek(0)
    return output.getvalue()


def _figure_to_png_bytes(fig):
    try:
        return pio.to_image(fig, format="png", width=1200, height=700, scale=2), None
    except Exception as exc:  # pragma: no cover - depends on local image engine
        return None, str(exc)


def _format_metric_value(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.4f}"


def _looks_like_datetime(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    non_null = series.dropna()
    if non_null.empty:
        return False

    parsed = pd.to_datetime(non_null, errors="coerce")
    return bool((parsed.notna().mean()) >= 0.8)


def _apply_slicer_filters(df: pd.DataFrame, prefix: str = "dax_slicer") -> pd.DataFrame:
    st.markdown("### Filtres interactifs (type Power BI)")
    st.caption("Ces filtres s'appliquent directement aux visuels et aux indicateurs de cette section.")

    with st.expander("Configurer les filtres", expanded=True):
        filter_cols = st.multiselect(
            "Colonnes a utiliser en filtres",
            options=df.columns.tolist(),
            key=f"{prefix}_cols",
        )

        filtered_df = df.copy()

        for col in filter_cols:
            safe_col_key = _safe_filename(col, fallback="col")
            series = filtered_df[col]
            st.markdown(f"**{col}**")

            if pd.api.types.is_numeric_dtype(series):
                numeric_series = pd.to_numeric(series, errors="coerce")
                valid = numeric_series.dropna()
                if valid.empty:
                    st.info("Aucune valeur numerique exploitable pour ce filtre.")
                    continue

                min_val = float(valid.min())
                max_val = float(valid.max())

                if min_val == max_val:
                    st.caption(f"Valeur unique: {min_val}")
                    filtered_df = filtered_df[numeric_series == min_val]
                else:
                    selected_range = st.slider(
                        f"Intervalle - {col}",
                        min_value=min_val,
                        max_value=max_val,
                        value=(min_val, max_val),
                        key=f"{prefix}_num_{safe_col_key}",
                    )
                    filtered_df = filtered_df[numeric_series.between(selected_range[0], selected_range[1])]
                continue

            if _looks_like_datetime(series):
                dt_series = pd.to_datetime(series, errors="coerce")
                valid = dt_series.dropna()
                if valid.empty:
                    st.info("Aucune valeur date exploitable pour ce filtre.")
                    continue

                min_date = valid.min().date()
                max_date = valid.max().date()
                selected_dates = st.date_input(
                    f"Periode - {col}",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key=f"{prefix}_date_{safe_col_key}",
                )

                if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                    start_date, end_date = selected_dates
                else:
                    start_date = selected_dates
                    end_date = selected_dates

                mask = dt_series.dt.date.between(start_date, end_date)
                filtered_df = filtered_df[mask.fillna(False)]
                continue

            values = sorted(filtered_df[col].dropna().astype(str).unique().tolist())
            selected_values = st.multiselect(
                f"Valeurs - {col}",
                options=values,
                default=values,
                key=f"{prefix}_cat_{safe_col_key}",
            )
            if not selected_values:
                filtered_df = filtered_df.iloc[0:0]
            else:
                filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_values)]

        metric_col1, metric_col2 = st.columns(2)
        metric_col1.metric("Lignes avant filtres", len(df))
        metric_col2.metric("Lignes apres filtres", len(filtered_df))

        if st.button("Reinitialiser les filtres", key=f"{prefix}_reset"):
            keys_to_remove = [key for key in st.session_state.keys() if key.startswith(f"{prefix}_")]
            for key in keys_to_remove:
                del st.session_state[key]
            st.rerun()

    return filtered_df


def main(df: pd.DataFrame) -> None:
    st.title("Modelisation DAX pour Power BI")

    if df is None or df.empty:
        st.info("Chargez un fichier pour activer la generation DAX.")
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    all_cols = df.columns.tolist()
    date_cols = [col for col in all_cols if _looks_like_datetime(df[col])]

    if "dax_snippets" not in st.session_state:
        st.session_state.dax_snippets = []

    if not numeric_cols:
        st.warning("Aucune colonne numerique detectee. Les options de mesure DAX sont limitees.")

    st.subheader("Parametrage")
    table_name = st.text_input("Nom de table DAX", value="Data")

    with st.expander("Dictionnaire de donnees"):
        profile = pd.DataFrame(
            {
                "Colonne": all_cols,
                "Type": [str(df[col].dtype) for col in all_cols],
                "Taux manquant (%)": (df.isna().mean() * 100).round(2).values,
            }
        )
        st.dataframe(profile, use_container_width=True)

    tab_basic, tab_time, tab_context, tab_advanced, tab_visual, tab_script = st.tabs(
        [
            "Mesures standard",
            "Intelligence temporelle",
            "Contexte de calcul",
            "Modeles avances",
            "Visualisation des scripts DAX",
            "Script consolide",
        ]
    )

    with tab_basic:
        st.write("Generez rapidement des mesures standard et des ratios.")

        if numeric_cols:
            metric_type = st.selectbox(
                "Type de mesure",
                ["Somme", "Moyenne", "Minimum", "Maximum", "Nombre de valeurs", "Nombre distinct", "Ratio"],
            )

            if metric_type == "Ratio":
                numerator_col = st.selectbox("Numerateur", numeric_cols, key="dax_num")
                denominator_col = st.selectbox("Denominateur", numeric_cols, key="dax_den")
                measure_name = st.text_input("Nom de la mesure", value=f"Taux {numerator_col}")
                formula = _build_ratio_measure(table_name, numerator_col, denominator_col, measure_name)
            else:
                target_col = st.selectbox("Colonne cible", numeric_cols, key="dax_basic_col")
                measure_name = st.text_input("Nom de la mesure", value=f"{metric_type} {target_col}")
                formula = _build_basic_measure(table_name, target_col, metric_type, measure_name)

            _show_snippet(formula, button_key="add_basic_formula")
        else:
            st.info("Ajoutez au moins une colonne numerique pour generer des mesures standard.")

    with tab_time:
        st.write("Modeles DAX pour les analyses temporelles (YTD, MTD, M-1, croissance).")

        if numeric_cols and date_cols:
            value_col = st.selectbox("Colonne valeur", numeric_cols, key="dax_time_value")
            date_col = st.selectbox("Colonne date", date_cols, key="dax_time_date")
            base_measure_name = st.text_input("Nom mesure de base", value=f"Total {value_col}")

            formulas = _build_time_intelligence_block(table_name, value_col, date_col, base_measure_name)
            full_block = "\n\n".join(formulas)
            _show_snippet(full_block, button_key="add_time_formula")
        else:
            st.info("Ce bloc requiert au moins une colonne numerique et une colonne de date.")

    with tab_context:
        st.write("Mesures de contexte: part du total et classement.")

        if all_cols:
            value_measure_name = st.text_input("Mesure de valeur existante", value="Total Ventes")
            dimension_col = st.selectbox("Dimension de classement", all_cols, key="dax_dimension")
            formulas = _build_context_block(table_name, value_measure_name, dimension_col)
            full_block = "\n\n".join(formulas)
            _show_snippet(full_block, button_key="add_context_formula")
        else:
            st.info("Aucune colonne disponible.")

    with tab_advanced:
        st.write("Modeles avances avec CALCULATE, FILTER, REMOVEFILTERS et SAMEPERIODLASTYEAR.")

        base_measure_name = st.text_input(
            "Mesure de base existante",
            value="Total Ventes",
            key="dax_adv_base_measure",
        )

        if all_cols:
            st.markdown("Filtre metier (CALCULATE + FILTER)")
            filter_col = st.selectbox("Colonne de filtre", all_cols, key="dax_adv_filter_col")
            filter_value = st.text_input("Valeur du filtre", value="", key="dax_adv_filter_value")
            filter_measure_name = st.text_input(
                "Nom mesure filtree",
                value=f"{base_measure_name} Filtre",
                key="dax_adv_filter_name",
            )
            if filter_value.strip():
                filter_formula = _build_filter_measure(
                    table_name,
                    base_measure_name,
                    filter_col,
                    filter_value.strip(),
                    filter_measure_name,
                )
                _show_snippet(filter_formula, button_key="add_adv_filter_formula")
            else:
                st.info("Renseignez une valeur de filtre pour generer la mesure filtree.")

            st.markdown("Suppression de filtres (CALCULATE + REMOVEFILTERS)")
            remove_scope = st.selectbox(
                "Portee REMOVEFILTERS",
                ["Table complete"] + all_cols,
                key="dax_adv_remove_scope",
            )
            remove_measure_name = st.text_input(
                "Nom mesure sans filtre",
                value=f"{base_measure_name} Global",
                key="dax_adv_remove_name",
            )
            scope_col = None if remove_scope == "Table complete" else remove_scope
            remove_formula = _build_removefilters_measure(
                table_name,
                base_measure_name,
                scope_col,
                remove_measure_name,
            )
            _show_snippet(remove_formula, button_key="add_adv_remove_formula")

            st.markdown("Classement Top N (CALCULATE + TOPN)")
            topn_col = st.selectbox("Dimension Top N", all_cols, key="dax_adv_topn_col")
            topn_n = st.slider("N", min_value=1, max_value=50, value=5, key="dax_adv_topn_n")
            topn_measure_name = st.text_input(
                "Nom mesure Top N",
                value=f"{base_measure_name} Top {topn_n}",
                key="dax_adv_topn_name",
            )
            topn_formula = _build_topn_measure(
                table_name,
                base_measure_name,
                topn_col,
                topn_n,
                topn_measure_name,
            )
            _show_snippet(topn_formula, button_key="add_adv_topn_formula")
        else:
            st.info("Aucune colonne disponible pour les modeles avances.")

        st.markdown("Comparaison avec l'annee precedente (SAMEPERIODLASTYEAR)")
        if date_cols:
            date_col = st.selectbox("Colonne date", date_cols, key="dax_adv_yoy_date")
            yoy_block = "\n\n".join(
                _build_yoy_block(base_measure_name=base_measure_name, date_ref=_dax_col_ref(table_name, date_col))
            )
            _show_snippet(yoy_block, button_key="add_adv_yoy_formula")
        else:
            st.info("Aucune colonne de date detectee pour la comparaison avec l'annee precedente.")

    with tab_visual:
        st.subheader("Visualisation des scripts DAX")
        st.write("Visualisez vos formules DAX dans l'application avec des filtres interactifs type Power BI.")

        source_mode = st.radio(
            "Source de la mesure",
            ["Utiliser une mesure du script DAX", "Construire une mesure"],
            horizontal=True,
        )

        metric_type = None
        target_col = None
        numerator_col = None
        denominator_col = None
        measure_name = "Mesure"
        formula = ""

        if source_mode == "Construire une mesure":
            metric_type = st.selectbox(
                "Type de mesure du visuel",
                ["Somme", "Moyenne", "Minimum", "Maximum", "Nombre de valeurs", "Nombre distinct", "Ratio"],
                key="dax_visual_metric_type",
            )

            if metric_type == "Ratio":
                if not numeric_cols:
                    st.info("Ajoutez des colonnes numeriques pour visualiser un ratio.")
                else:
                    numerator_col = st.selectbox("Numerateur", numeric_cols, key="dax_visual_num")
                    denominator_col = st.selectbox("Denominateur", numeric_cols, key="dax_visual_den")
                    measure_name = st.text_input("Nom de la mesure", value=f"Taux {numerator_col}", key="dax_visual_name_ratio")
                    formula = _build_ratio_measure(table_name, numerator_col, denominator_col, measure_name)
            else:
                candidate_cols = all_cols if metric_type in {"Nombre de valeurs", "Nombre distinct"} else numeric_cols
                if not candidate_cols:
                    st.info("Aucune colonne compatible pour ce type de mesure.")
                else:
                    target_col = st.selectbox("Colonne cible", candidate_cols, key="dax_visual_target")
                    measure_name = st.text_input(
                        "Nom de la mesure",
                        value=f"{metric_type} {target_col}",
                        key="dax_visual_name_basic",
                    )
                    formula = _build_basic_measure(table_name, target_col, metric_type, measure_name)

            if formula:
                st.code(formula, language="sql")
                if st.button("Ajouter cette mesure au script", key="add_visual_formula"):
                    _store_snippet(formula)
                    st.success("La mesure a ete ajoutee au script DAX.")

        else:
            if not st.session_state.dax_snippets:
                st.info("Aucune mesure disponible dans le script DAX. Ajoutez d'abord des mesures.")
            else:
                selected_index = st.selectbox(
                    "Mesure a visualiser",
                    options=list(range(len(st.session_state.dax_snippets))),
                    format_func=lambda i: f"{i + 1}. {_first_formula_line(st.session_state.dax_snippets[i])[:100]}",
                    key="dax_visual_existing_measure",
                )
                selected_snippet = st.session_state.dax_snippets[selected_index]
                first_line = _first_formula_line(selected_snippet)
                parsed = _parse_supported_measure(first_line)

                st.code(selected_snippet, language="sql")
                if parsed is None:
                    st.warning(
                        "Cette mesure n'est pas compatible avec la previsualisation automatique. "
                        "Expressions prises en charge: SUM, AVERAGE, MIN, MAX, COUNT, DISTINCTCOUNT, DIVIDE(SUM,SUM)."
                    )
                else:
                    metric_type = parsed["metric_type"]
                    target_col = parsed["target_col"]
                    numerator_col = parsed["numerator_col"]
                    denominator_col = parsed["denominator_col"]
                    measure_name = parsed["measure_name"]
                    formula = parsed["formula"]
                    st.caption("Previsualisation basee sur la premiere formule de la mesure selectionnee.")

        filtered_df = _apply_slicer_filters(df, prefix="dax_visual_filter")

        if filtered_df.empty:
            st.warning("Aucune ligne ne correspond aux filtres actifs. Ajustez les slicers.")
        elif metric_type is None:
            st.info("Configurez d'abord une mesure pour afficher une visualisation.")
        else:
            validation_error = _validate_metric_spec(filtered_df, metric_type, target_col, numerator_col, denominator_col)
            if validation_error:
                st.warning(validation_error)
            else:
                st.caption(f"Base utilisee pour le calcul: {len(filtered_df):,} lignes apres filtrage.")

                dimension_choice = st.selectbox(
                    "Dimension du visuel",
                    ["(Aucune - indicateur global)"] + all_cols,
                    key="dax_visual_dimension",
                )
                dimension_col = None if dimension_choice.startswith("(Aucune") else dimension_choice

                chart_type = None
                top_n = 20
                if dimension_col is not None:
                    chart_type = st.selectbox(
                        "Type de graphique",
                        ["Barres", "Ligne", "Aire", "Camembert"],
                        key="dax_visual_chart_type",
                    )
                    top_n = st.slider("Top N lignes", min_value=3, max_value=100, value=20, key="dax_visual_top_n")

                st.markdown("### Resultats")

                export_df = pd.DataFrame()
                fig = None

                if dimension_col is None:
                    metric_value = _compute_metric_global(
                        filtered_df, metric_type, target_col, numerator_col, denominator_col
                    )
                    st.metric(measure_name, _format_metric_value(metric_value))
                    export_df = pd.DataFrame({"Mesure": [measure_name], "Valeur": [metric_value]})
                else:
                    grouped_df = _compute_metric_by_dimension(
                        df=filtered_df,
                        dimension_col=dimension_col,
                        metric_type=metric_type,
                        measure_name=measure_name,
                        target_col=target_col,
                        numerator_col=numerator_col,
                        denominator_col=denominator_col,
                    )
                    if grouped_df.empty:
                        st.info("Aucune donnee exploitable pour cette visualisation.")
                    else:
                        visual_df = _prepare_visual_dataframe(grouped_df, dimension_col, measure_name, chart_type, top_n)
                        st.dataframe(visual_df, use_container_width=True)
                        fig = _build_visual_figure(visual_df, dimension_col, measure_name, chart_type)
                        if fig is not None:
                            st.plotly_chart(fig, use_container_width=True)
                        export_df = visual_df

                if not export_df.empty:
                    st.markdown("### Export des resultats")
                    base_name = _safe_filename(f"{measure_name}_visual")

                    csv_bytes = export_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                    excel_bytes = _to_excel_bytes(export_df)

                    col_csv, col_xlsx, col_html, col_png = st.columns(4)
                    with col_csv:
                        st.download_button(
                            "Exporter CSV",
                            data=csv_bytes,
                            file_name=f"{base_name}.csv",
                            mime="text/csv",
                        )

                    with col_xlsx:
                        st.download_button(
                            "Exporter Excel",
                            data=excel_bytes,
                            file_name=f"{base_name}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )

                    with col_html:
                        if fig is not None:
                            html_bytes = fig.to_html(include_plotlyjs="cdn", full_html=True).encode("utf-8")
                            st.download_button(
                                "Exporter HTML",
                                data=html_bytes,
                                file_name=f"{base_name}.html",
                                mime="text/html",
                            )
                        else:
                            st.download_button(
                                "Exporter TXT",
                                data=f"{measure_name} = {export_df.iloc[0]['Valeur']}\n\n{formula}".encode("utf-8"),
                                file_name=f"{base_name}.txt",
                                mime="text/plain",
                            )

                    with col_png:
                        if fig is not None:
                            png_bytes, png_error = _figure_to_png_bytes(fig)
                            if png_bytes is not None:
                                st.download_button(
                                    "Exporter l'image PNG",
                                    data=png_bytes,
                                    file_name=f"{base_name}.png",
                                    mime="image/png",
                                )
                            else:
                                st.caption("PNG indisponible sur cet environnement.")
                                st.caption(png_error[:140])
                        else:
                            st.write("")

    with tab_script:
        st.write("Assemblez vos mesures puis exportez-les dans un fichier unique.")

        script_text = "\n\n".join(st.session_state.dax_snippets).strip()
        st.text_area("Script DAX consolide", value=script_text, height=280)

        col1, col2 = st.columns(2)
        with col1:
            if script_text:
                st.download_button(
                    "Telecharger le script .dax",
                    data=script_text,
                    file_name="mesures.dax",
                    mime="text/plain",
                )
            else:
                st.info("Ajoutez des mesures depuis les autres onglets.")

        with col2:
            if st.button("Reinitialiser le script"):
                st.session_state.dax_snippets = []
                st.success("Le script DAX a ete reinitialise.")


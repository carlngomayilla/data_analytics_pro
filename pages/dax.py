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


def _ensure_unique_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    seen: dict[str, int] = {}
    used: set[str] = set()
    new_cols: list[str] = []
    renames: list[tuple[str, str]] = []

    for original in df.columns.tolist():
        base = str(original)
        count = seen.get(base, 0) + 1
        seen[base] = count

        if count == 1 and base not in used:
            candidate = base
        else:
            suffix = count
            candidate = f"{base}__{suffix}"
            while candidate in used:
                suffix += 1
                candidate = f"{base}__{suffix}"

        used.add(candidate)
        new_cols.append(candidate)
        if candidate != base:
            renames.append((base, candidate))

    if not renames and all(str(col) == col for col in df.columns.tolist()):
        return df, []

    out = df.copy()
    out.columns = new_cols
    return out, renames


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


def _as_series(df: pd.DataFrame, col: str) -> pd.Series:
    selected = df.loc[:, col]
    if isinstance(selected, pd.DataFrame):
        # If source columns are duplicated, keep the first physical column.
        return selected.iloc[:, 0]
    return selected


def _find_column_exact(columns: list[str], desired: str) -> str | None:
    desired_norm = (desired or "").strip().lower()
    if not desired_norm:
        return None
    for col in columns:
        if str(col).strip().lower() == desired_norm:
            return col
    return None


def _pick_column_by_keywords(columns: list[str], keywords: list[str]) -> str | None:
    lowered = [(col, str(col).lower()) for col in columns]
    for keyword in keywords:
        key = keyword.lower()
        for col, low in lowered:
            if key in low:
                return col
    return None


def _extract_script_measure_specs(snippets: list[str]) -> dict[str, dict]:
    specs: dict[str, dict] = {}
    for snippet in snippets:
        parsed = _parse_supported_measure(_first_formula_line(snippet))
        if parsed is None:
            continue
        specs[parsed["measure_name"]] = parsed
    return specs


def _default_powerbi_measure_specs(df: pd.DataFrame, table_name: str = "Data") -> dict[str, dict]:
    all_cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not all_cols:
        return {}

    amount_col = _pick_column_by_keywords(
        numeric_cols,
        ["depense", "montant", "amount", "prix", "price", "cout", "cost", "valeur", "vente", "sales", "total"],
    )
    if amount_col is None and numeric_cols:
        amount_col = numeric_cols[0]

    count_col = _pick_column_by_keywords(all_cols, ["id", "numero", "num", "reference", "ref"])
    if count_col is None:
        count_col = amount_col if amount_col is not None else all_cols[0]

    specs: dict[str, dict] = {}
    if amount_col is not None:
        specs["Total Dépenses"] = {
            "measure_name": "Total Dépenses",
            "metric_type": "Somme",
            "target_col": amount_col,
            "numerator_col": None,
            "denominator_col": None,
            "formula": _build_basic_measure(table_name, amount_col, "Somme", "Total Dépenses"),
        }
        specs["Panier Moyen"] = {
            "measure_name": "Panier Moyen",
            "metric_type": "Moyenne",
            "target_col": amount_col,
            "numerator_col": None,
            "denominator_col": None,
            "formula": _build_basic_measure(table_name, amount_col, "Moyenne", "Panier Moyen"),
        }
        specs["% du Total (tous services)"] = {
            "measure_name": "% du Total (tous services)",
            "metric_type": "Part du total",
            "target_col": amount_col,
            "numerator_col": None,
            "denominator_col": None,
            "formula": (
                f"% du Total (tous services) = "
                f"DIVIDE([Mesure], CALCULATE([Mesure], ALL({_dax_table_ref(table_name)})), 0)"
            ),
        }

    specs["Nb Dépenses"] = {
        "measure_name": "Nb Dépenses",
        "metric_type": "Nombre de valeurs",
        "target_col": count_col,
        "numerator_col": None,
        "denominator_col": None,
        "formula": _build_basic_measure(table_name, count_col, "Nombre de valeurs", "Nb Dépenses"),
    }
    return specs


def _build_time_drilldown_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    date_candidates = [col for col in df.columns if _looks_like_datetime(df[col])]
    if not date_candidates:
        return df, {}

    base_col = date_candidates[0]
    parsed = pd.to_datetime(df[base_col], errors="coerce")
    if not parsed.notna().any():
        return df, {}

    enriched = df.copy()
    enriched["__dax_year__"] = parsed.dt.year.astype("Int64")
    enriched["__dax_month__"] = parsed.dt.to_period("M").astype("string")
    enriched["__dax_day__"] = parsed.dt.date.astype("string")
    return enriched, {"Année": "__dax_year__", "Mois": "__dax_month__", "Jour": "__dax_day__"}


def _compute_powerbi_visual_df(
    df: pd.DataFrame,
    axis_col: str,
    metric_spec: dict,
    top_n: int | str,
) -> pd.DataFrame:
    metric_type = metric_spec["metric_type"]
    measure_name = metric_spec["measure_name"]
    target_col = metric_spec["target_col"]
    numerator_col = metric_spec["numerator_col"]
    denominator_col = metric_spec["denominator_col"]

    if metric_type == "Part du total":
        grouped = _compute_metric_by_dimension(
            df=df,
            dimension_col=axis_col,
            metric_type="Somme",
            measure_name=measure_name,
            target_col=target_col,
            numerator_col=None,
            denominator_col=None,
        )
        total = _to_numeric(_as_series(df, target_col)).sum(min_count=1)
        if pd.isna(total) or float(total) == 0.0:
            grouped[measure_name] = 0.0
        else:
            grouped[measure_name] = (grouped[measure_name] / float(total)) * 100.0
        result = grouped
    else:
        result = _compute_metric_by_dimension(
            df=df,
            dimension_col=axis_col,
            metric_type=metric_type,
            measure_name=measure_name,
            target_col=target_col,
            numerator_col=numerator_col,
            denominator_col=denominator_col,
        )

    if result.empty:
        return result

    time_axes = {"__dax_year__", "__dax_month__", "__dax_day__"}
    if axis_col in time_axes:
        parsed_dates = pd.to_datetime(result[axis_col], errors="coerce")
        if parsed_dates.notna().any():
            result["_sort_time"] = parsed_dates
            result = result.sort_values("_sort_time", ascending=True).drop(columns=["_sort_time"])
        else:
            result = result.sort_values(axis_col, ascending=True)
    else:
        result = result.sort_values(measure_name, ascending=False)

    if top_n != "Tous" and axis_col not in time_axes:
        result = result.head(int(top_n))

    return result


def _compute_metric_from_spec(df: pd.DataFrame, metric_spec: dict) -> float:
    metric_type = metric_spec["metric_type"]
    target_col = metric_spec["target_col"]
    numerator_col = metric_spec["numerator_col"]
    denominator_col = metric_spec["denominator_col"]

    if metric_type == "Part du total":
        return _compute_metric_global(
            df=df,
            metric_type="Somme",
            target_col=target_col,
            numerator_col=None,
            denominator_col=None,
        )

    return _compute_metric_global(
        df=df,
        metric_type=metric_type,
        target_col=target_col,
        numerator_col=numerator_col,
        denominator_col=denominator_col,
    )


def _compute_metric_global(
    df: pd.DataFrame,
    metric_type: str,
    target_col: str | None,
    numerator_col: str | None,
    denominator_col: str | None,
) -> float:
    if metric_type == "Ratio":
        numerator = _to_numeric(_as_series(df, numerator_col)).sum()
        denominator = _to_numeric(_as_series(df, denominator_col)).sum()
        if pd.isna(denominator) or float(denominator) == 0.0:
            return 0.0
        return float(numerator / denominator)

    if metric_type == "Somme":
        return float(_to_numeric(_as_series(df, target_col)).sum())
    if metric_type == "Moyenne":
        return float(_to_numeric(_as_series(df, target_col)).mean())
    if metric_type == "Minimum":
        return float(_to_numeric(_as_series(df, target_col)).min())
    if metric_type == "Maximum":
        return float(_to_numeric(_as_series(df, target_col)).max())
    if metric_type == "Nombre de valeurs":
        return float(_as_series(df, target_col).count())
    if metric_type == "Nombre distinct":
        return float(_as_series(df, target_col).nunique(dropna=True))

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
    dim_series = _as_series(df, dimension_col)
    work = pd.DataFrame({"__dim__": dim_series}, index=df.index)

    if metric_type == "Ratio":
        work["__num__"] = _to_numeric(_as_series(df, numerator_col))
        work["__den__"] = _to_numeric(_as_series(df, denominator_col))
        grouped = work.groupby("__dim__", dropna=False)
        numerator = grouped["__num__"].sum(min_count=1)
        denominator = grouped["__den__"].sum(min_count=1)
        values = numerator / denominator.replace(0, pd.NA)
    else:
        work["__val__"] = _as_series(df, target_col)
        if metric_type in {"Somme", "Moyenne", "Minimum", "Maximum"}:
            work["__val__"] = pd.to_numeric(work["__val__"], errors="coerce")

        grouped = work.groupby("__dim__", dropna=False)["__val__"]
        if metric_type == "Somme":
            values = grouped.sum(min_count=1)
        elif metric_type == "Moyenne":
            values = grouped.mean()
        elif metric_type == "Minimum":
            values = grouped.min()
        elif metric_type == "Maximum":
            values = grouped.max()
        elif metric_type == "Nombre de valeurs":
            values = grouped.count()
        elif metric_type == "Nombre distinct":
            values = grouped.nunique(dropna=True)
        else:
            return pd.DataFrame(columns=[dimension_col, measure_name])

    result = values.reset_index(name=measure_name).rename(columns={"__dim__": dimension_col})
    result[measure_name] = pd.to_numeric(result[measure_name], errors="coerce")
    result[dimension_col] = result[dimension_col].astype("string").fillna("(Vide)")
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

    df, renamed_cols = _ensure_unique_columns(df)
    if renamed_cols:
        preview_pairs = [f"`{old}` -> `{new}`" for old, new in renamed_cols[:6]]
        preview_text = ", ".join(preview_pairs)
        if len(renamed_cols) > 6:
            preview_text += f", ... (+{len(renamed_cols) - 6})"
        st.warning(
            "Colonnes dupliquees detectees. "
            "Pour eviter les erreurs de groupement, cette page utilise des noms uniques: "
            f"{preview_text}"
        )

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
        st.subheader("Power BI-like : Mesures + Visuels")

        measure_catalog = {
            "Finance": ["Total Dépenses", "Panier Moyen", "% du Total (tous services)"],
            "Volume": ["Nb Dépenses"],
        }

        filtered_df = _apply_slicer_filters(df, prefix="dax_visual_filter")
        if filtered_df.empty:
            st.warning("Aucune ligne ne correspond aux filtres actifs. Ajustez les slicers.")
        else:
            default_specs = _default_powerbi_measure_specs(filtered_df, table_name=table_name)
            script_specs = _extract_script_measure_specs(st.session_state.dax_snippets)
            measure_specs = {**default_specs, **script_specs}

            if not measure_specs:
                st.info("Aucune mesure exploitable. Ajoutez des mesures ou chargez des colonnes numeriques.")
            else:
                all_measures = [m for grp in measure_catalog.values() for m in grp if m in measure_specs]
                if not all_measures:
                    all_measures = list(measure_specs.keys())

                colA, colB, colC, colD = st.columns([1.2, 1.2, 1, 1])

                with colA:
                    measure_group = st.selectbox(
                        "Groupe de mesures",
                        list(measure_catalog.keys()),
                        index=0,
                        key="dax_pbi_group",
                    )
                with colB:
                    measures_in_group = [m for m in measure_catalog.get(measure_group, []) if m in measure_specs]
                    if not measures_in_group:
                        measures_in_group = all_measures
                    selected_measure = st.selectbox(
                        "Mesure",
                        measures_in_group,
                        index=0,
                        key="dax_pbi_measure",
                    )
                with colC:
                    chart_type = st.selectbox("Visuel", ["Bar", "Line", "Area", "Pie"], index=0, key="dax_pbi_chart")
                with colD:
                    top_n = st.selectbox("Top N", [5, 10, 15, 20, "Tous"], index=1, key="dax_pbi_topn")

                visual_source_df, time_level_map = _build_time_drilldown_columns(filtered_df)

                dim_choices = []
                dim_map: dict[str, str] = {}

                for preferred in ["service", "direction", "type"]:
                    found = _find_column_exact(visual_source_df.columns.tolist(), preferred)
                    if found is not None:
                        dim_choices.append(found)
                        dim_map[found] = found

                if not dim_choices:
                    fallback_dims = [c for c in visual_source_df.columns.tolist() if not str(c).startswith("__dax_")]
                    fallback_dims = fallback_dims[: min(6, len(fallback_dims))]
                    dim_choices = fallback_dims
                    dim_map.update({col: col for col in fallback_dims})

                if time_level_map:
                    dim_choices.append("Temps (drilldown)")
                    dim_map["Temps (drilldown)"] = "__time__"

                if not dim_choices:
                    st.warning("Aucune dimension disponible pour construire un visuel.")
                else:
                    dim_choice = st.selectbox("Axe (dimension)", dim_choices, index=0, key="dax_pbi_dimension")

                    if dim_choice == "Temps (drilldown)":
                        time_level = st.radio(
                            "Niveau temps",
                            ["Année", "Mois", "Jour"],
                            horizontal=True,
                            key="dax_pbi_time_level",
                        )
                        dim_col = time_level_map.get(time_level)
                    else:
                        dim_col = dim_map[dim_choice]

                    metric_spec = measure_specs[selected_measure]
                    metric_type = metric_spec["metric_type"]
                    target_col = metric_spec["target_col"]
                    numerator_col = metric_spec["numerator_col"]
                    denominator_col = metric_spec["denominator_col"]

                    validation_error = _validate_metric_spec(
                        visual_source_df,
                        "Somme" if metric_type == "Part du total" else metric_type,
                        target_col,
                        numerator_col,
                        denominator_col,
                    )
                    if validation_error:
                        st.warning(validation_error)
                    else:
                        st.code(metric_spec["formula"], language="sql")
                        st.caption(f"Base utilisee pour le calcul: {len(visual_source_df):,} lignes apres filtrage.")

                        vis_df = _compute_powerbi_visual_df(
                            df=visual_source_df,
                            axis_col=dim_col,
                            metric_spec=metric_spec,
                            top_n=top_n,
                        )

                        if vis_df.empty:
                            st.warning("Aucune donnee pour ce visuel avec les filtres actuels.")
                        else:
                            axis_label = dim_col
                            display_df = vis_df.copy()
                            if dim_col == "__dax_year__":
                                axis_label = "year"
                                display_df = display_df.rename(columns={dim_col: axis_label})
                            elif dim_col == "__dax_month__":
                                axis_label = "month"
                                display_df = display_df.rename(columns={dim_col: axis_label})
                            elif dim_col == "__dax_day__":
                                axis_label = "date"
                                display_df = display_df.rename(columns={dim_col: axis_label})

                            measure_col = metric_spec["measure_name"]
                            st.dataframe(display_df, use_container_width=True)

                            title = f"{selected_measure} par {axis_label}"
                            if chart_type == "Bar":
                                fig = px.bar(display_df, x=axis_label, y=measure_col, title=title)
                            elif chart_type == "Line":
                                fig = px.line(display_df, x=axis_label, y=measure_col, markers=True, title=title)
                            elif chart_type == "Area":
                                fig = px.area(display_df, x=axis_label, y=measure_col, title=title)
                            else:
                                fig = px.pie(display_df, names=axis_label, values=measure_col, title=title)

                            st.plotly_chart(fig, use_container_width=True)

                            st.markdown("### Filtre par selection (Power BI-like)")
                            axis_values = list(dict.fromkeys(display_df[axis_label].astype(str).tolist()))
                            selected_axis_value = st.selectbox(
                                f"Appliquer un filtre sur {axis_label}",
                                options=["(aucun)"] + axis_values,
                                key="dax_pbi_axis_filter",
                            )

                            if selected_axis_value != "(aucun)":
                                axis_series = visual_source_df[dim_col].astype("string").fillna("(Vide)")
                                selected_df = visual_source_df[axis_series == str(selected_axis_value)]

                                st.markdown("#### KPIs sous selection")
                                k1, k2, k3 = st.columns(3)
                                for col, kpi_name in zip(
                                    [k1, k2, k3],
                                    ["Total Dépenses", "Nb Dépenses", "Panier Moyen"],
                                ):
                                    kpi_spec = measure_specs.get(kpi_name)
                                    if kpi_spec is None:
                                        col.metric(kpi_name, "N/A")
                                    else:
                                        kpi_value = _compute_metric_from_spec(selected_df, kpi_spec)
                                        col.metric(kpi_name, _format_metric_value(kpi_value))

                            st.markdown("### Export des resultats")
                            base_name = _safe_filename(f"{selected_measure}_visual")
                            csv_bytes = display_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                            excel_bytes = _to_excel_bytes(display_df)
                            html_bytes = fig.to_html(include_plotlyjs="cdn", full_html=True).encode("utf-8")
                            png_bytes, png_error = _figure_to_png_bytes(fig)

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
                                st.download_button(
                                    "Exporter HTML",
                                    data=html_bytes,
                                    file_name=f"{base_name}.html",
                                    mime="text/html",
                                )
                            with col_png:
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


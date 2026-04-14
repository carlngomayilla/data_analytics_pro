import warnings
from datetime import date, datetime

import pandas as pd
import streamlit as st


# Explication: Nettoie un nom pour creer une cle Streamlit stable et sans caracteres problematiques.
def _safe_key(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(name))
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "col"


# Explication: Recupere une colonne en serie pandas, ou une serie vide si la colonne est absente.
def _as_series(df: pd.DataFrame, col: str) -> pd.Series:
    selected = df.loc[:, col]
    if isinstance(selected, pd.DataFrame):
        return selected.iloc[:, 0]
    return selected


# Explication: Convertit une colonne en dates/heures, meme si les formats sont heterogenes.
def _to_datetime_series(series: pd.Series) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
        except (TypeError, ValueError, OverflowError):
            try:
                parsed = pd.to_datetime(series, errors="coerce")
            except (TypeError, ValueError, OverflowError):
                parsed = None

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

    # Explication: Convertit une valeur texte en date quand c'est possible.
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


# Explication: Detecte rapidement si une colonne ressemble a des dates.
def _looks_like_datetime(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    non_null = series.dropna()
    if non_null.empty:
        return False
    parsed = _to_datetime_series(non_null)
    return bool((parsed.notna().mean()) >= 0.8)


# Explication: Construit un objet qui sauvegarde l'etat actuel des filtres.
def _build_preset_payload(df: pd.DataFrame, prefix: str, selected_cols: list[str]) -> dict:
    widget_values: dict[str, object] = {}
    for col in selected_cols:
        if col not in df.columns:
            continue
        safe_col = _safe_key(col)
        series = _as_series(df, col)
        if pd.api.types.is_numeric_dtype(series):
            key = f"{prefix}_num_{safe_col}"
            if key in st.session_state:
                widget_values[key] = st.session_state[key]
        elif _looks_like_datetime(series):
            key = f"{prefix}_date_{safe_col}"
            if key in st.session_state:
                widget_values[key] = st.session_state[key]
        else:
            key = f"{prefix}_cat_{safe_col}"
            if key in st.session_state:
                widget_values[key] = st.session_state[key]

    return {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "selected_cols": [col for col in selected_cols if col in df.columns],
        "widget_values": widget_values,
    }


# Explication: Recharge un preset de filtres dans l'interface utilisateur.
def _apply_preset(prefix: str, payload: dict, df: pd.DataFrame) -> None:
    selected_cols = [col for col in payload.get("selected_cols", []) if col in df.columns]
    st.session_state[f"{prefix}_enabled"] = True
    st.session_state[f"{prefix}_cols"] = selected_cols

    widget_values = payload.get("widget_values", {})
    for key, value in widget_values.items():
        st.session_state[key] = value


# Explication: Affiche les filtres globaux et retourne le DataFrame apres filtrage.
def apply_global_filters(
    df: pd.DataFrame,
    prefix: str = "global_filter",
) -> tuple[pd.DataFrame, dict]:
    if df is None or df.empty:
        return df, {"enabled": False, "active_filters": 0}

    presets_key = f"{prefix}_presets"
    if presets_key not in st.session_state:
        st.session_state[presets_key] = {}
    presets: dict = st.session_state[presets_key]

    with st.sidebar:
        st.markdown("---")
        st.subheader("Filtres globaux")
        enabled = st.checkbox(
            "Activer les filtres globaux",
            value=st.session_state.get(f"{prefix}_enabled", False),
            key=f"{prefix}_enabled",
        )

        preset_names = sorted(presets.keys())
        selected_preset = st.selectbox(
            "Preset de filtres",
            options=["(aucun)"] + preset_names,
            key=f"{prefix}_preset_select",
        )

        preset_col1, preset_col2 = st.columns(2)
        with preset_col1:
            if st.button("Appliquer preset", key=f"{prefix}_preset_apply", disabled=selected_preset == "(aucun)"):
                payload = presets.get(selected_preset)
                if payload is not None:
                    _apply_preset(prefix, payload, df)
                    st.success(f"Preset applique: {selected_preset}")
                    st.rerun()
        with preset_col2:
            if st.button("Supprimer preset", key=f"{prefix}_preset_delete", disabled=selected_preset == "(aucun)"):
                if selected_preset in presets:
                    del presets[selected_preset]
                    st.session_state[presets_key] = presets
                    st.success(f"Preset supprime: {selected_preset}")
                    st.rerun()

        if not enabled:
            return df, {"enabled": False, "active_filters": 0}

        selected_cols = st.multiselect(
            "Colonnes a filtrer",
            options=df.columns.tolist(),
            key=f"{prefix}_cols",
        )

        filtered_df = df.copy()
        active_filters = 0

        for col in selected_cols:
            if col not in filtered_df.columns:
                continue
            series = _as_series(filtered_df, col)
            safe_col = _safe_key(col)
            st.caption(f"Filtre global: {col}")

            if pd.api.types.is_numeric_dtype(series):
                numeric_series = pd.to_numeric(series, errors="coerce")
                valid = numeric_series.dropna()
                if valid.empty:
                    st.caption("Aucune valeur numerique exploitable.")
                    continue

                min_val = float(valid.min())
                max_val = float(valid.max())
                key = f"{prefix}_num_{safe_col}"

                if min_val == max_val:
                    st.caption(f"Valeur unique: {min_val}")
                    selected_range = (min_val, max_val)
                else:
                    default_range = st.session_state.get(key, (min_val, max_val))
                    if not isinstance(default_range, (tuple, list)) or len(default_range) != 2:
                        default_range = (min_val, max_val)
                    low = float(default_range[0]) if default_range[0] is not None else min_val
                    high = float(default_range[1]) if default_range[1] is not None else max_val
                    low = min(max(low, min_val), max_val)
                    high = max(min(high, max_val), min_val)
                    if low > high:
                        low, high = min_val, max_val
                    selected_range = st.slider(
                        f"Intervalle - {col}",
                        min_value=min_val,
                        max_value=max_val,
                        value=(low, high),
                        key=key,
                    )

                filtered_df = filtered_df[numeric_series.between(float(selected_range[0]), float(selected_range[1]))]
                if float(selected_range[0]) > min_val or float(selected_range[1]) < max_val:
                    active_filters += 1
                continue

            if _looks_like_datetime(series):
                dt_series = _to_datetime_series(series)
                valid = dt_series.dropna()
                if valid.empty:
                    st.caption("Aucune valeur date exploitable.")
                    continue

                min_date = valid.min().date()
                max_date = valid.max().date()
                key = f"{prefix}_date_{safe_col}"
                default_period = st.session_state.get(key, (min_date, max_date))
                if not isinstance(default_period, (tuple, list)) or len(default_period) != 2:
                    default_period = (min_date, max_date)

                start_default = default_period[0] if isinstance(default_period[0], date) else min_date
                end_default = default_period[1] if isinstance(default_period[1], date) else max_date
                if start_default > end_default:
                    start_default, end_default = min_date, max_date

                selected_period = st.date_input(
                    f"Periode - {col}",
                    value=(start_default, end_default),
                    min_value=min_date,
                    max_value=max_date,
                    key=key,
                )
                if isinstance(selected_period, tuple) and len(selected_period) == 2:
                    start_date, end_date = selected_period
                else:
                    start_date = selected_period
                    end_date = selected_period

                mask = dt_series.dt.date.between(start_date, end_date)
                filtered_df = filtered_df[mask.fillna(False)]
                if start_date > min_date or end_date < max_date:
                    active_filters += 1
                continue

            values = sorted(series.dropna().astype(str).unique().tolist())
            key = f"{prefix}_cat_{safe_col}"
            if not values:
                st.caption("Aucune valeur disponible.")
                continue

            default_values = st.session_state.get(key, values)
            if not isinstance(default_values, list):
                default_values = values
            default_values = [value for value in default_values if value in values]
            if not default_values:
                default_values = values

            selected_values = st.multiselect(
                f"Valeurs - {col}",
                options=values,
                default=default_values,
                key=key,
            )

            if not selected_values:
                filtered_df = filtered_df.iloc[0:0]
                active_filters += 1
            else:
                filtered_df = filtered_df[series.astype(str).isin(selected_values)]
                if set(selected_values) != set(values):
                    active_filters += 1

        st.caption(f"Resultat filtres globaux: {len(filtered_df):,} / {len(df):,} lignes")

        preset_name = st.text_input(
            "Nom du preset",
            placeholder="ex: Finance_Q1",
            key=f"{prefix}_preset_name",
        )
        if st.button("Sauvegarder le preset courant", key=f"{prefix}_preset_save"):
            name = (preset_name or "").strip()
            if not name:
                st.warning("Renseignez un nom de preset.")
            else:
                presets[name] = _build_preset_payload(df, prefix, selected_cols)
                st.session_state[presets_key] = presets
                st.success(f"Preset enregistre: {name}")

    return filtered_df, {"enabled": True, "active_filters": active_filters}

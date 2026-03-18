import warnings
from typing import Any

import pandas as pd


# Explication: Convertit une colonne en dates/heures, meme si les formats sont heterogenes.
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

    # Explication: Convertit une valeur texte en date quand c'est possible.
    def _parse_value(value: Any):
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


# Explication: Identifie les types reels presents dans une colonne declaree en objet.
def _object_type_names(series: pd.Series) -> list[str]:
    non_null = series.dropna()
    if non_null.empty:
        return []
    type_names = sorted({type(value).__name__ for value in non_null})
    return type_names


# Explication: Harmonise les types de colonnes (date, nombre, texte) pour faciliter l'analyse.
def normalize_dataframe_types(
    df: pd.DataFrame,
    numeric_threshold: float = 0.92,
    datetime_threshold: float = 0.88,
) -> tuple[pd.DataFrame, dict]:
    """
    Normalise les types de colonnes instables (object/string) pour limiter
    les erreurs d'analyse/affichage (Arrow, groupby, filtres).
    """
    normalized = df.copy()
    report = {
        "numeric_converted": [],
        "datetime_converted": [],
        "forced_string": [],
        "suspect_columns": [],
    }

    text_cols = normalized.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in text_cols:
        source = normalized[col]
        non_null = source.dropna()
        if non_null.empty:
            continue

        as_text = source.astype("string").str.strip()
        non_empty = as_text.dropna()
        non_empty = non_empty[non_empty != ""]
        if non_empty.empty:
            continue

        object_types = _object_type_names(source)
        mixed_object_types = len(object_types) > 1

        numeric_candidate = pd.to_numeric(non_empty.str.replace(",", ".", regex=False), errors="coerce")
        numeric_ratio = float(numeric_candidate.notna().mean())

        dt_candidate = _to_datetime_series(non_empty)
        datetime_ratio = float(dt_candidate.notna().mean())

        converted = False
        if numeric_ratio >= numeric_threshold and numeric_ratio >= datetime_ratio:
            normalized[col] = pd.to_numeric(
                as_text.str.replace(",", ".", regex=False),
                errors="coerce",
            )
            report["numeric_converted"].append(col)
            converted = True
        elif datetime_ratio >= datetime_threshold:
            normalized[col] = _to_datetime_series(source)
            report["datetime_converted"].append(col)
            converted = True

        if converted:
            continue

        if mixed_object_types:
            normalized[col] = source.astype("string")
            report["forced_string"].append(col)

        if 0.35 <= max(numeric_ratio, datetime_ratio) < max(numeric_threshold, datetime_threshold):
            report["suspect_columns"].append(
                {
                    "column": col,
                    "types": object_types,
                    "numeric_ratio": round(numeric_ratio, 3),
                    "datetime_ratio": round(datetime_ratio, 3),
                }
            )

    return normalized, report


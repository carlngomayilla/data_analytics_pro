import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    silhouette_score,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

try:
    from xgboost import XGBClassifier, XGBRegressor

    XGBOOST_AVAILABLE = True
except Exception:
    XGBClassifier = None
    XGBRegressor = None
    XGBOOST_AVAILABLE = False

RANDOM_STATE = 42


def _safe_dataframe_display(dataframe: pd.DataFrame) -> None:
    try:
        st.dataframe(dataframe, use_container_width=True)
    except OverflowError:
        st.warning(
            "Certaines valeurs sont trop grandes pour l'affichage natif. "
            "Conversion en texte appliquee."
        )
        st.dataframe(dataframe.astype(str), use_container_width=True)


def _infer_task(target: pd.Series) -> str:
    non_null = target.dropna()
    if non_null.empty:
        return "Classification"
    if pd.api.types.is_numeric_dtype(non_null):
        unique_count = non_null.nunique(dropna=True)
        return "Regression" if unique_count > 15 else "Classification"
    return "Classification"


def _build_preprocessor(x_train: pd.DataFrame) -> ColumnTransformer:
    numeric_cols = x_train.select_dtypes(include="number").columns.tolist()
    categorical_cols = [col for col in x_train.columns if col not in numeric_cols]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ]
    )


def _model_options(task: str) -> list[str]:
    if task == "Regression":
        options = [
            "LinearRegression",
            "RandomForestRegressor",
            "GradientBoostingRegressor",
        ]
        if XGBOOST_AVAILABLE:
            options.append("XGBRegressor")
        return options

    options = [
        "LogisticRegression",
        "RandomForestClassifier",
        "GradientBoostingClassifier",
    ]
    if XGBOOST_AVAILABLE:
        options.append("XGBClassifier")
    return options


def _build_model(task: str, model_name: str):
    if task == "Regression":
        if model_name == "LinearRegression":
            return LinearRegression()
        if model_name == "RandomForestRegressor":
            return RandomForestRegressor(
                n_estimators=300,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
        if model_name == "XGBRegressor" and XGBOOST_AVAILABLE:
            return XGBRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=RANDOM_STATE,
                n_jobs=-1,
                objective="reg:squarederror",
            )
        return GradientBoostingRegressor(random_state=RANDOM_STATE)

    if model_name == "LogisticRegression":
        return LogisticRegression(max_iter=2000)
    if model_name == "RandomForestClassifier":
        return RandomForestClassifier(
            n_estimators=300,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
    if model_name == "XGBClassifier" and XGBOOST_AVAILABLE:
        return XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
    return GradientBoostingClassifier(random_state=RANDOM_STATE)


def _cv_splitter(task: str, y: pd.Series, requested_folds: int):
    max_by_rows = int(len(y))
    if max_by_rows < 2:
        return None, "Pas assez de lignes pour la validation croisee."

    if task == "Classification":
        class_counts = y.value_counts()
        if class_counts.empty:
            return None, "Cible vide, validation croisee impossible."
        max_by_class = int(class_counts.min())
        n_splits = min(requested_folds, max_by_rows, max_by_class)
        if n_splits < 2:
            return None, "Au moins 2 observations par classe sont necessaires pour la CV."
        return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE), None

    n_splits = min(requested_folds, max_by_rows)
    if n_splits < 2:
        return None, "Pas assez de lignes pour la CV en regression."
    return KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE), None


def _run_cross_validation(
    pipeline: Pipeline,
    x: pd.DataFrame,
    y: pd.Series,
    task: str,
    requested_folds: int,
) -> dict:
    splitter, error = _cv_splitter(task, y, requested_folds)
    if splitter is None:
        return {"error": error}

    if task == "Regression":
        scoring_map = {
            "R2": "r2",
            "MAE": "neg_mean_absolute_error",
            "RMSE": "neg_root_mean_squared_error",
        }
    else:
        scoring_map = {
            "Accuracy": "accuracy",
            "Precision": "precision_weighted",
            "Recall": "recall_weighted",
            "F1": "f1_weighted",
        }

    rows = []
    for metric_name, scorer in scoring_map.items():
        scores = cross_val_score(
            pipeline,
            x,
            y,
            cv=splitter,
            scoring=scorer,
            n_jobs=1,
        )
        if scorer.startswith("neg_"):
            scores = -scores
        rows.append(
            {
                "Metrique": metric_name,
                "Moyenne": float(np.mean(scores)),
                "Ecart-type": float(np.std(scores)),
                "Min": float(np.min(scores)),
                "Max": float(np.max(scores)),
            }
        )

    return {
        "folds": int(splitter.get_n_splits()),
        "table": pd.DataFrame(rows),
    }


def _can_stratify(y: pd.Series) -> bool:
    return y.nunique() > 1 and y.value_counts().min() >= 2


def _regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    mse = mean_squared_error(y_true, y_pred)
    rmse = float(np.sqrt(mse))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    denom = np.where(np.abs(y_true) < 1e-12, np.nan, np.abs(y_true))
    mape = np.nanmean(np.abs((y_true - y_pred) / denom)) * 100
    if np.isnan(mape):
        mape = 0.0

    return {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "R2": float(r2),
        "MAPE (%)": float(mape),
    }


def _classification_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "Accuracy": float(accuracy_score(y_true, y_pred)),
        "Precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "Recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "F1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }


def _feature_importance(
    trained_pipeline: Pipeline,
    top_n: int = 20,
) -> pd.DataFrame | None:
    preprocessor = trained_pipeline.named_steps["preprocessor"]
    model = trained_pipeline.named_steps["model"]

    if not hasattr(preprocessor, "get_feature_names_out"):
        return None

    feature_names = np.array(preprocessor.get_feature_names_out(), dtype=str)
    scores = None

    if hasattr(model, "feature_importances_"):
        scores = np.asarray(model.feature_importances_)
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_)
        if coef.ndim == 1:
            scores = np.abs(coef)
        else:
            scores = np.mean(np.abs(coef), axis=0)

    if scores is None or len(scores) != len(feature_names):
        return None

    importance_df = pd.DataFrame(
        {
            "Feature": feature_names,
            "Importance": scores,
        }
    ).sort_values("Importance", ascending=False)
    return importance_df.head(top_n)


def _display_supervised_results(result: dict) -> None:
    st.subheader("Resultats du modele")
    st.caption(
        f"Modele: {result['model_name']} | Cible: {result['target']} | "
        f"Lignes train/test: {result['train_rows']}/{result['test_rows']}"
    )

    metrics = result["metrics"]
    metric_cols = st.columns(len(metrics))
    for idx, (name, value) in enumerate(metrics.items()):
        metric_cols[idx].metric(name, f"{value:.4f}")

    cv_result = result.get("cv_result")
    if cv_result:
        st.subheader("Validation croisee")
        if cv_result.get("error"):
            st.warning(cv_result["error"])
        else:
            st.caption(f"CV executee avec {cv_result['folds']} folds.")
            _safe_dataframe_display(cv_result["table"].round(4))

    _safe_dataframe_display(result["comparison"])

    if result.get("task") == "Classification" and result.get("confusion_matrix") is not None:
        st.subheader("Matrice de confusion")
        cm_df = result["confusion_matrix"]
        fig_cm = px.imshow(
            cm_df,
            text_auto=True,
            color_continuous_scale="Blues",
            labels={"x": "Predit", "y": "Reel", "color": "Volume"},
            title="Matrice de confusion",
        )
        st.plotly_chart(fig_cm, use_container_width=True)

    importance_df = result.get("feature_importance")
    if importance_df is not None and not importance_df.empty:
        st.subheader("Importance des variables")
        fig_imp = px.bar(
            importance_df.sort_values("Importance"),
            x="Importance",
            y="Feature",
            orientation="h",
            title="Top variables explicatives",
        )
        st.plotly_chart(fig_imp, use_container_width=True)


def _render_supervised_tab(df: pd.DataFrame) -> None:
    st.subheader("Apprentissage supervise")

    if len(df.columns) < 2:
        st.info("Il faut au moins 2 colonnes pour entrainer un modele supervise.")
        return

    target_col = st.selectbox("Variable cible", df.columns.tolist(), key="ml_target")
    candidate_features = [col for col in df.columns if col != target_col]
    selected_features = st.multiselect(
        "Variables explicatives",
        candidate_features,
        default=candidate_features,
        key="ml_features",
    )

    if not selected_features:
        st.warning("Selectionnez au moins une variable explicative.")
        return

    inferred_task = _infer_task(df[target_col])
    task_options = ["Classification", "Regression"]
    task = st.radio(
        "Type de probleme",
        task_options,
        index=task_options.index(inferred_task),
        horizontal=True,
        key="ml_task",
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        test_size = st.slider(
            "Part du jeu de test",
            min_value=0.1,
            max_value=0.4,
            value=0.2,
            step=0.05,
            key="ml_test_size",
        )
    with col_b:
        model_name = st.selectbox(
            "Modele",
            _model_options(task),
            key="ml_model_name",
        )
    with col_c:
        cv_enabled = st.checkbox("Validation croisee", value=True, key="ml_cv_enabled")
        cv_folds = st.slider(
            "Folds CV",
            min_value=3,
            max_value=10,
            value=5,
            step=1,
            key="ml_cv_folds",
            disabled=not cv_enabled,
        )

    if not XGBOOST_AVAILABLE:
        st.caption("XGBoost n'est pas disponible dans cet environnement.")

    if st.button("Entrainer le modele", key="ml_train_button"):
        train_df = df[selected_features + [target_col]].copy()
        train_df = train_df.dropna(subset=[target_col])

        if train_df.empty or len(train_df) < 10:
            st.error("Pas assez de lignes exploitables apres suppression des cibles manquantes.")
            return

        x = train_df[selected_features]
        y = train_df[target_col]
        target_encoder = None
        y_model = y

        if task == "Regression":
            y = pd.to_numeric(y, errors="coerce")
            valid_idx = y.notna()
            x = x.loc[valid_idx]
            y_model = y.loc[valid_idx]
            if len(y_model) < 10:
                st.error("La cible de regression doit contenir des valeurs numeriques.")
                return
        else:
            y = y.astype(str)
            if y.nunique() < 2:
                st.error("La classification exige au moins 2 classes distinctes.")
                return
            if model_name == "XGBClassifier":
                target_encoder = LabelEncoder()
                y_model = pd.Series(target_encoder.fit_transform(y), index=y.index)
            else:
                y_model = y

        stratify = y_model if task == "Classification" and _can_stratify(y_model) else None
        try:
            x_train, x_test, y_train, y_test = train_test_split(
                x,
                y_model,
                test_size=test_size,
                random_state=RANDOM_STATE,
                stratify=stratify,
            )
        except ValueError:
            x_train, x_test, y_train, y_test = train_test_split(
                x,
                y_model,
                test_size=test_size,
                random_state=RANDOM_STATE,
                stratify=None,
            )

        pipeline = Pipeline(
            steps=[
                ("preprocessor", _build_preprocessor(x_train)),
                ("model", _build_model(task, model_name)),
            ]
        )

        cv_result = None
        with st.spinner("Entrainement du modele en cours..."):
            if cv_enabled:
                cv_result = _run_cross_validation(
                    pipeline=pipeline,
                    x=x,
                    y=y_model,
                    task=task,
                    requested_folds=cv_folds,
                )
            pipeline.fit(x_train, y_train)
            y_pred = pipeline.predict(x_test)

        if task == "Regression":
            metrics = _regression_metrics(y_test, y_pred)
            comparison = pd.DataFrame(
                {
                    "Reel": y_test.values,
                    "Predit": y_pred,
                    "Erreur absolue": np.abs(y_test.values - y_pred),
                }
            ).head(200)
            confusion_df = None
        else:
            if target_encoder is not None:
                y_test_display = target_encoder.inverse_transform(np.asarray(y_test, dtype=int))
                y_pred_display = target_encoder.inverse_transform(np.asarray(y_pred, dtype=int))
            else:
                y_test_display = np.asarray(y_test).astype(str)
                y_pred_display = np.asarray(y_pred).astype(str)

            metrics = _classification_metrics(
                pd.Series(y_test_display),
                np.asarray(y_pred_display),
            )
            comparison = pd.DataFrame(
                {
                    "Reel": y_test_display,
                    "Predit": y_pred_display,
                }
            ).head(200)
            labels = np.unique(np.concatenate([np.asarray(y_test_display), np.asarray(y_pred_display)]))
            cm = confusion_matrix(y_test_display, y_pred_display, labels=labels)
            confusion_df = pd.DataFrame(cm, index=labels, columns=labels)

        feature_imp = _feature_importance(pipeline, top_n=20)

        st.session_state.ml_supervised_model = pipeline
        st.session_state.ml_supervised_context = {
            "task": task,
            "target": target_col,
            "features": selected_features,
            "model_name": model_name,
            "metrics": metrics,
            "comparison": comparison,
            "confusion_matrix": confusion_df,
            "feature_importance": feature_imp,
            "cv_result": cv_result,
            "target_encoder": target_encoder,
            "train_rows": int(len(x_train)),
            "test_rows": int(len(x_test)),
        }
        st.success("Modele entraine avec succes.")

    result = st.session_state.get("ml_supervised_context")
    if result:
        _display_supervised_results(result)


def _render_clustering_tab(df: pd.DataFrame) -> None:
    st.subheader("Clustering K-Means")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if len(numeric_cols) < 2:
        st.info("K-Means exige au moins 2 colonnes numeriques.")
        return

    selected_cols = st.multiselect(
        "Variables numeriques pour le clustering",
        numeric_cols,
        default=numeric_cols[: min(4, len(numeric_cols))],
        key="ml_kmeans_cols",
    )
    if len(selected_cols) < 2:
        st.warning("Selectionnez au moins 2 colonnes numeriques.")
        return

    max_k = min(12, max(2, len(df) - 1))
    default_k = min(3, max_k)

    cluster_count = st.slider(
        "Nombre de clusters (k)",
        min_value=2,
        max_value=max_k,
        value=default_k,
        step=1,
        key="ml_kmeans_k",
    )
    normalize = st.checkbox("Standardiser les variables", value=True, key="ml_kmeans_norm")
    cluster_col_name = st.text_input(
        "Nom de la colonne cluster a ajouter",
        value=f"cluster_k{cluster_count}",
        key="ml_cluster_col_name",
    ).strip()

    if st.button("Executer K-Means", key="ml_kmeans_run"):
        cluster_df = df[selected_cols].dropna().copy()
        if len(cluster_df) <= cluster_count:
            st.error("Le nombre de lignes valides doit etre superieur au nombre de clusters.")
            return

        matrix = cluster_df.values
        if normalize:
            matrix = StandardScaler().fit_transform(matrix)

        kmeans = KMeans(
            n_clusters=cluster_count,
            random_state=RANDOM_STATE,
            n_init=10,
        )
        labels = kmeans.fit_predict(matrix)

        silhouette = None
        if cluster_count >= 2 and len(cluster_df) > cluster_count:
            silhouette = float(silhouette_score(matrix, labels))

        clustered = cluster_df.copy()
        clustered["cluster"] = labels

        st.session_state.ml_clustering_context = {
            "selected_cols": selected_cols,
            "cluster_count": cluster_count,
            "labels_index": clustered.index.tolist(),
            "labels_values": labels.tolist(),
            "clustered_preview": clustered.head(300),
            "cluster_sizes": clustered["cluster"].value_counts().sort_index(),
            "inertia": float(kmeans.inertia_),
            "silhouette": silhouette,
            "cluster_col_name": cluster_col_name if cluster_col_name else f"cluster_k{cluster_count}",
        }
        st.success("Clustering termine.")

    cluster_result = st.session_state.get("ml_clustering_context")
    if not cluster_result:
        return

    col1, col2 = st.columns(2)
    col1.metric("Inertie", f"{cluster_result['inertia']:.4f}")
    silhouette = cluster_result.get("silhouette")
    col2.metric("Silhouette", f"{silhouette:.4f}" if silhouette is not None else "N/A")

    st.subheader("Taille des clusters")
    cluster_sizes = cluster_result["cluster_sizes"].rename_axis("cluster").reset_index(name="effectif")
    _safe_dataframe_display(cluster_sizes)

    st.subheader("Apercu des donnees clusterisees")
    _safe_dataframe_display(cluster_result["clustered_preview"])

    plot_cols = cluster_result["selected_cols"][:2]
    scatter_df = cluster_result["clustered_preview"].copy()
    scatter_df["cluster"] = scatter_df["cluster"].astype(str)
    fig = px.scatter(
        scatter_df,
        x=plot_cols[0],
        y=plot_cols[1],
        color="cluster",
        title=f"Visualisation des clusters ({plot_cols[0]} vs {plot_cols[1]})",
    )
    st.plotly_chart(fig, use_container_width=True)

    if st.button("Ajouter les clusters a la base active", key="ml_apply_clusters"):
        new_col = cluster_result["cluster_col_name"]
        updated = st.session_state.df.copy()
        updated[new_col] = pd.NA
        updated.loc[cluster_result["labels_index"], new_col] = cluster_result["labels_values"]
        st.session_state.df = updated
        st.session_state.pop("cleaning_df", None)
        st.session_state.pop("cleaning_source_signature", None)
        st.success(f"Colonne '{new_col}' ajoutee a la base active.")
        st.rerun()


def _prediction_input_widget(df: pd.DataFrame, feature: str):
    series = df[feature]
    key_prefix = f"ml_pred_{feature}"

    if pd.api.types.is_numeric_dtype(series):
        default = float(series.dropna().median()) if series.notna().any() else 0.0
        return st.number_input(f"{feature}", value=default, key=f"{key_prefix}_num")

    if pd.api.types.is_datetime64_any_dtype(series):
        default_txt = ""
        if series.notna().any():
            default_txt = str(series.dropna().iloc[0])
        return st.text_input(
            f"{feature} (datetime, ex: 2025-01-31 12:30:00)",
            value=default_txt,
            key=f"{key_prefix}_dt",
        )

    choices = sorted(series.dropna().astype(str).unique().tolist())
    if 0 < len(choices) <= 200:
        return st.selectbox(f"{feature}", choices, key=f"{key_prefix}_cat")
    return st.text_input(f"{feature}", value="", key=f"{key_prefix}_txt")


def _render_prediction_tab(df: pd.DataFrame) -> None:
    st.subheader("Prediction sur nouvelle observation")

    model = st.session_state.get("ml_supervised_model")
    context = st.session_state.get("ml_supervised_context")
    if model is None or context is None:
        st.info("Entrainez d'abord un modele supervise pour activer cette section.")
        return

    st.caption(
        f"Modele actif: {context['model_name']} | Type: {context['task']} | "
        f"Cible: {context['target']}"
    )

    features = context["features"]
    with st.form("ml_prediction_form"):
        input_values = {}
        for feature in features:
            input_values[feature] = _prediction_input_widget(df, feature)

        submitted = st.form_submit_button("Predire")

    if not submitted:
        return

    input_df = pd.DataFrame([input_values])

    for feature in features:
        source_col = df[feature]
        if pd.api.types.is_numeric_dtype(source_col):
            input_df[feature] = pd.to_numeric(input_df[feature], errors="coerce")
        elif pd.api.types.is_datetime64_any_dtype(source_col):
            input_df[feature] = pd.to_datetime(input_df[feature], errors="coerce")
        else:
            input_df[feature] = input_df[feature].astype(str)

    target_encoder = context.get("target_encoder")

    try:
        prediction = model.predict(input_df)[0]
    except Exception as exc:
        st.error(f"Echec de prediction: {exc}")
        return

    prediction_display = prediction
    if context["task"] == "Classification" and target_encoder is not None:
        try:
            prediction_display = target_encoder.inverse_transform([int(prediction)])[0]
        except Exception:
            prediction_display = prediction

    st.success(f"Prediction: {prediction_display}")

    if context["task"] == "Classification" and hasattr(model, "predict_proba"):
        try:
            probas = model.predict_proba(input_df)[0]
            classes = model.classes_
            if target_encoder is not None:
                classes = target_encoder.inverse_transform(classes.astype(int))
            proba_df = pd.DataFrame(
                {
                    "Classe": classes.astype(str),
                    "Probabilite": probas,
                }
            ).sort_values("Probabilite", ascending=False)
            st.subheader("Probabilites par classe")
            _safe_dataframe_display(proba_df)
        except Exception:
            st.caption("Probabilites indisponibles pour ce modele.")


def main(df: pd.DataFrame) -> None:
    st.title("Module Machine Learning")

    if df is None or df.empty:
        st.info("Chargez des donnees pour commencer.")
        return

    tab1, tab2, tab3 = st.tabs(
        [
            "Apprentissage supervise",
            "Clustering K-Means",
            "Prediction",
        ]
    )

    with tab1:
        _render_supervised_tab(df)
    with tab2:
        _render_clustering_tab(df)
    with tab3:
        _render_prediction_tab(df)

# core/ml_engine.py
import streamlit as st
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_squared_error
from xgboost import XGBClassifier, XGBRegressor
from config.settings import ML_THRESHOLD

def run_ml(df, target):
    if target not in df.columns:
        st.error("Cible non trouvée")
        return

    X = df.drop(target, axis=1)
    y = df[target]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Détection auto : classification ou régression
    is_classification = len(y.unique()) < 10  # Arbitrary threshold

    model = RandomForestClassifier() if is_classification else RandomForestRegressor()
    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    score = accuracy_score(y_test, pred) if is_classification else mean_squared_error(y_test, pred)
    st.success(f"Score : {score}")

    # XGBoost alternatif
    xgb = XGBClassifier() if is_classification else XGBRegressor()
    xgb.fit(X_train, y_train)
    xgb_pred = xgb.predict(X_test)
    xgb_score = accuracy_score(y_test, xgb_pred) if is_classification else mean_squared_error(y_test, xgb_pred)
    st.success(f"XGBoost Score : {xgb_score}")

    # Seuil pour classification
    if is_classification:
        proba = model.predict_proba(X_test)[:, 1]
        st.write(f"Predictions au seuil {ML_THRESHOLD} : {sum(proba > ML_THRESHOLD)} positives")
# config/settings.py
# Toutes les configurations centrales

APP_TITLE = "Nexus Data Analytics Pro"
APP_SUBTITLE = "Plateforme d'analyse decisionnelle"

# DOMAINS_AVAILABLE = ["*", "Finance", "Marketing", "Ventes", "RH"]

SAMPLE_DATA_OPTIONS = {
    "Aucun": None,
    "Exemple Finance": "data_examples/finance.csv",
    "Exemple Ventes": "data_examples/sales.csv",
}

UPLOAD_FOLDER = "uploaded_data"
DATA_EXAMPLE_FOLDER = "data_examples"
MAX_FILE_SIZE_MB = 200

DARK_THEME_CSS = """
<style>
/* Background principal */
.stApp {
    background-color: #0e1117;
    color: #f1f1f1;
    font-family: 'Segoe UI', sans-serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #1a1d24;
    border-right: 1px solid #2e313a;
}

/* Header */
header {
    background-color: #0e1117 !important;
}

/* Boutons */
.stButton>button {
    background: linear-gradient(135deg, #7b2ff7, #f107a3);
    color: white;
    border-radius: 8px;
    border: none;
    padding: 0.5em 1em;
    transition: 0.3s ease-in-out;
}

.stButton>button:hover {
    transform: scale(1.05);
    box-shadow: 0px 0px 15px rgba(123, 47, 247, 0.5);
}

/* Inputs */
.stTextInput>div>div>input,
.stNumberInput input,
.stSelectbox div {
    background-color: #1e222a;
    color: #ffffff;
    border-radius: 6px;
    border: 1px solid #3a3f4b;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    background-color: #1e222a;
}

/* Cards */
div[data-testid="stMetric"] {
    background-color: #1a1d24;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0px 0px 10px rgba(0,0,0,0.5);
}
</style>
"""

LIGHT_THEME_CSS = """
<style>
/* Background principal */
.stApp {
    background-color: #f9fafc;
    color: #1f1f1f;
    font-family: 'Segoe UI', sans-serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
}

/* Boutons */
.stButton>button {
    background: linear-gradient(135deg, #4facfe, #00f2fe);
    color: white;
    border-radius: 8px;
    border: none;
    padding: 0.5em 1em;
    transition: 0.3s ease-in-out;
}

.stButton>button:hover {
    transform: scale(1.05);
    box-shadow: 0px 0px 10px rgba(79, 172, 254, 0.4);
}

/* Inputs */
.stTextInput>div>div>input,
.stNumberInput input,
.stSelectbox div {
    background-color: #ffffff;
    color: #000000;
    border-radius: 6px;
    border: 1px solid #dcdcdc;
}

/* Cards */
div[data-testid="stMetric"] {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
}
</style>
"""

# ML configuration
ML_TARGET_DEFAULT = None
ML_THRESHOLD = 0.5

# Messages
WELCOME_MESSAGE = "Bienvenue. Chargez vos donnees pour commencer."
ERROR_MESSAGE = "Erreur: "
SUCCESS_MESSAGE = "Operation reussie: "



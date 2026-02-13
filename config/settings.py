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
    .stApp {background-color: #0e1117; color: #fafafa;}
    section[data-testid="stSidebar"] {background-color: #262730;}
    header {background-color: #0e1117 !important;}
</style>
"""

LIGHT_THEME_CSS = """
<style>
    .stApp {background-color: #ffffff; color: #000000;}
    section[data-testid="stSidebar"] {background-color: #f0f2f6;}
</style>
"""

# ML configuration
ML_TARGET_DEFAULT = None
ML_THRESHOLD = 0.5

# Messages
WELCOME_MESSAGE = "Bienvenue. Chargez vos donnees pour commencer."
ERROR_MESSAGE = "Erreur: "
SUCCESS_MESSAGE = "Operation reussie: "


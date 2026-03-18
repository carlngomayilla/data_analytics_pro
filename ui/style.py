# ui/style.py
import streamlit as st


# Explication: Applique le style CSS de l'interface selon le theme choisi.
def style_css(theme):
    if theme == "dark":
        st.markdown(
            """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

            html, body, [class*="css"] {
                font-family: "Inter", sans-serif;
            }

            :root {
                --bg-main: #05040A;
                --bg-card: rgba(255, 255, 255, 0.05);
                --bg-card-2: rgba(255, 255, 255, 0.03);
                --border: rgba(255, 255, 255, 0.12);

                --text: #F8F7FF;
                --text-soft: rgba(248, 247, 255, 0.72);

                --violet: #8B5CF6;
                --violet-light: #A78BFA;
                --violet-glow: rgba(139, 92, 246, 0.35);

                --radius-xl: 20px;
                --radius-lg: 14px;

                --shadow: 0 12px 30px rgba(0, 0, 0, 0.45);
            }

            .stApp {
                background:
                    radial-gradient(circle at 20% 10%, rgba(139, 92, 246, .20), transparent 45%),
                    radial-gradient(circle at 80% 15%, rgba(167, 139, 250, .15), transparent 45%),
                    linear-gradient(180deg, #040308 0%, #05040A 100%);
                color: var(--text);
            }

            section.main > div {
                padding-top: 1.4rem;
            }

            section[data-testid="stSidebar"] {
                background: linear-gradient(
                    180deg,
                    rgba(139, 92, 246, .12),
                    rgba(255, 255, 255, .03)
                );
                border-right: 1px solid var(--border);
            }

            section[data-testid="stSidebar"] * {
                color: var(--text) !important;
            }

            h1 {
                font-weight: 800;
                letter-spacing: -0.02em;
            }

            h2, h3 {
                font-weight: 700;
            }

            .card,
            div[data-testid="stMetric"],
            div[data-testid="stDataFrame"],
            div[data-testid="stTable"] {
                background: linear-gradient(
                    180deg,
                    var(--bg-card),
                    var(--bg-card-2)
                );
                border: 1px solid var(--border);
                border-radius: var(--radius-xl);
                box-shadow: var(--shadow);
                backdrop-filter: blur(8px);
                padding: 1rem;
            }

            .stButton > button {
                background: linear-gradient(
                    135deg,
                    var(--violet),
                    var(--violet-light)
                );
                color: white;
                font-weight: 650;
                border: none;
                border-radius: 12px;
                padding: 0.6rem 1.1rem;
                box-shadow: 0 10px 26px var(--violet-glow);
                transition: all .15s ease;
            }

            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 14px 34px var(--violet-glow);
            }

            .stButton > button:active {
                transform: scale(.98);
            }

            div[data-baseweb="input"] > div,
            div[data-baseweb="select"] > div,
            div[data-baseweb="textarea"] > div {
                background: rgba(255, 255, 255, .05) !important;
                border: 1px solid var(--border) !important;
                border-radius: 12px !important;
            }

            div[data-baseweb="input"] > div:focus-within,
            div[data-baseweb="select"] > div:focus-within {
                border-color: var(--violet) !important;
                box-shadow: 0 0 0 3px var(--violet-glow) !important;
            }

            label {
                color: var(--text-soft) !important;
                font-weight: 600 !important;
            }

            div[data-testid="stMetricLabel"] {
                color: var(--text-soft) !important;
                font-weight: 600 !important;
            }

            div[data-testid="stMetricValue"] {
                font-weight: 800 !important;
                letter-spacing: -0.02em;
            }

            div[data-testid="stTabs"] button {
                background: rgba(255, 255, 255, .04) !important;
                border: 1px solid var(--border) !important;
                border-radius: 999px !important;
                color: var(--text-soft) !important;
                padding: .45rem .9rem !important;
            }

            div[data-testid="stTabs"] button[aria-selected="true"] {
                background: rgba(139, 92, 246, .25) !important;
                border-color: rgba(139, 92, 246, .6) !important;
                color: var(--text) !important;
                box-shadow: 0 0 0 2px var(--violet-glow);
            }

            details {
                background: rgba(255, 255, 255, .04);
                border: 1px solid var(--border);
                border-radius: var(--radius-lg);
                padding: .4rem;
            }

            div[data-testid="stAlert"] {
                border-radius: var(--radius-lg);
                border: 1px solid var(--border);
                background: rgba(139, 92, 246, .12);
            }

            div[data-testid="stDataFrame"] {
                overflow: hidden;
            }

            hr {
                border: none;
                height: 1px;
                background: linear-gradient(
                    90deg,
                    transparent,
                    rgba(255, 255, 255, .2),
                    transparent
                );
            }
        </style>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
        <style>
            .stApp { background-color: #ffffff; color: #000000; }
            section[data-testid="stSidebar"] { background-color: #f0f2f6; }
            h1, h2, h3 { color: #111827; }
            .stButton > button {
                border-radius: 10px;
                border: 1px solid #d1d5db;
                font-weight: 600;
            }
        </style>
        """,
            unsafe_allow_html=True,
        )


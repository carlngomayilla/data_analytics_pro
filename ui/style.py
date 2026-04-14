# ui/style.py
import streamlit as st


def _build_theme_tokens(theme: str) -> dict[str, str]:
    if theme == "light":
        return {
            "app_bg": "#f5f7f4",
            "surface": "#ffffff",
            "surface_muted": "#edf2ee",
            "surface_soft": "#f8faf7",
            "sidebar_bg": "#111411",
            "sidebar_surface": "#1b211c",
            "text": "#161a16",
            "text_soft": "#5c665e",
            "sidebar_text": "#f6f8f4",
            "border": "#d8dfd7",
            "border_strong": "#b8c5ba",
            "accent": "#0f766e",
            "accent_2": "#b45309",
            "accent_3": "#be123c",
            "accent_soft": "rgba(15, 118, 110, 0.13)",
            "shadow": "0 14px 34px rgba(25, 33, 27, 0.10)",
            "plot_bg": "#ffffff",
        }

    return {
        "app_bg": "#10120f",
        "surface": "#181b17",
        "surface_muted": "#20261f",
        "surface_soft": "#151814",
        "sidebar_bg": "#0c0f0c",
        "sidebar_surface": "#151a15",
        "text": "#f3f6ef",
        "text_soft": "#b8c3b7",
        "sidebar_text": "#f3f6ef",
        "border": "#303a31",
        "border_strong": "#465448",
        "accent": "#2dd4bf",
        "accent_2": "#f59e0b",
        "accent_3": "#fb7185",
        "accent_soft": "rgba(45, 212, 191, 0.13)",
        "shadow": "0 16px 40px rgba(0, 0, 0, 0.38)",
        "plot_bg": "#131712",
    }


# Explication: Applique le style CSS de l'interface selon le theme choisi.
def style_css(theme):
    tokens = _build_theme_tokens(theme)
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            :root {{
                --nexus-app-bg: {tokens["app_bg"]};
                --nexus-surface: {tokens["surface"]};
                --nexus-surface-muted: {tokens["surface_muted"]};
                --nexus-surface-soft: {tokens["surface_soft"]};
                --nexus-sidebar-bg: {tokens["sidebar_bg"]};
                --nexus-sidebar-surface: {tokens["sidebar_surface"]};
                --nexus-text: {tokens["text"]};
                --nexus-text-soft: {tokens["text_soft"]};
                --nexus-sidebar-text: {tokens["sidebar_text"]};
                --nexus-border: {tokens["border"]};
                --nexus-border-strong: {tokens["border_strong"]};
                --nexus-accent: {tokens["accent"]};
                --nexus-accent-2: {tokens["accent_2"]};
                --nexus-accent-3: {tokens["accent_3"]};
                --nexus-accent-soft: {tokens["accent_soft"]};
                --nexus-shadow: {tokens["shadow"]};
                --nexus-radius: 8px;
                --nexus-radius-sm: 6px;
            }}

            html, body, [class*="css"], .stApp {{
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                letter-spacing: 0;
            }}

            .stApp {{
                color: var(--nexus-text);
                background:
                    linear-gradient(180deg, rgba(15, 118, 110, 0.10), transparent 260px),
                    linear-gradient(90deg, rgba(245, 158, 11, 0.05), transparent 360px),
                    var(--nexus-app-bg);
            }}

            header[data-testid="stHeader"] {{
                background: transparent;
            }}

            section.main > div,
            div[data-testid="stAppViewContainer"] > .main .block-container {{
                padding-top: 1.25rem;
                padding-bottom: 2rem;
                max-width: 1240px;
            }}

            section[data-testid="stSidebar"] {{
                background:
                    linear-gradient(180deg, rgba(15, 118, 110, 0.22), transparent 240px),
                    var(--nexus-sidebar-bg);
                border-right: 1px solid var(--nexus-border);
            }}

            section[data-testid="stSidebar"] * {{
                color: var(--nexus-sidebar-text) !important;
            }}

            section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p,
            section[data-testid="stSidebar"] label {{
                color: rgba(243, 246, 239, 0.78) !important;
            }}

            h1, h2, h3 {{
                color: var(--nexus-text);
                letter-spacing: 0;
            }}

            h1 {{
                font-weight: 800;
                line-height: 1.05;
            }}

            h2, h3 {{
                font-weight: 700;
            }}

            p, li, label, div[data-testid="stMarkdownContainer"] {{
                color: var(--nexus-text);
            }}

            small, caption, .caption, div[data-testid="stCaptionContainer"],
            div[data-testid="stMetricLabel"] {{
                color: var(--nexus-text-soft) !important;
            }}

            .stButton > button,
            .stDownloadButton > button,
            button[kind="primary"],
            button[kind="secondary"] {{
                border-radius: var(--nexus-radius) !important;
                border: 1px solid var(--nexus-border-strong) !important;
                background: linear-gradient(135deg, var(--nexus-accent), #0f8f7f) !important;
                color: #ffffff !important;
                font-weight: 700 !important;
                min-height: 2.6rem;
                box-shadow: 0 10px 24px rgba(15, 118, 110, 0.22);
                transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
            }}

            .stButton > button:hover,
            .stDownloadButton > button:hover {{
                border-color: var(--nexus-accent) !important;
                box-shadow: 0 14px 30px rgba(15, 118, 110, 0.28);
                transform: translateY(-1px);
            }}

            .stButton > button:active,
            .stDownloadButton > button:active {{
                transform: translateY(0);
            }}

            div[data-baseweb="input"] > div,
            div[data-baseweb="select"] > div,
            div[data-baseweb="textarea"] > div,
            div[data-baseweb="base-input"] {{
                background: var(--nexus-surface) !important;
                border: 1px solid var(--nexus-border) !important;
                border-radius: var(--nexus-radius) !important;
                color: var(--nexus-text) !important;
            }}

            div[data-baseweb="input"] > div:focus-within,
            div[data-baseweb="select"] > div:focus-within,
            div[data-baseweb="textarea"] > div:focus-within {{
                border-color: var(--nexus-accent) !important;
                box-shadow: 0 0 0 3px var(--nexus-accent-soft) !important;
            }}

            div[data-testid="stMetric"],
            div[data-testid="stDataFrame"],
            div[data-testid="stTable"] {{
                background: var(--nexus-surface);
                border: 1px solid var(--nexus-border);
                border-radius: var(--nexus-radius);
                box-shadow: var(--nexus-shadow);
                padding: 0.9rem;
            }}

            div[data-testid="stMetric"] {{
                border-left: 4px solid var(--nexus-accent);
            }}

            div[data-testid="stMetricValue"] {{
                color: var(--nexus-text) !important;
                font-weight: 800 !important;
                letter-spacing: 0;
            }}

            div[data-testid="stTabs"] button {{
                background: var(--nexus-surface-muted) !important;
                border: 1px solid var(--nexus-border) !important;
                border-radius: var(--nexus-radius) !important;
                color: var(--nexus-text-soft) !important;
                font-weight: 700 !important;
                padding: 0.45rem 0.85rem !important;
            }}

            div[data-testid="stTabs"] button[aria-selected="true"] {{
                background: var(--nexus-accent-soft) !important;
                border-color: var(--nexus-accent) !important;
                color: var(--nexus-text) !important;
            }}

            div[data-testid="stAlert"],
            details {{
                background: var(--nexus-surface-soft) !important;
                border: 1px solid var(--nexus-border) !important;
                border-radius: var(--nexus-radius) !important;
                box-shadow: none !important;
            }}

            hr {{
                border: none;
                height: 1px;
                background: linear-gradient(90deg, transparent, var(--nexus-border-strong), transparent);
            }}

            .nexus-hero {{
                border: 1px solid var(--nexus-border);
                border-radius: var(--nexus-radius);
                background:
                    linear-gradient(135deg, rgba(15, 118, 110, 0.20), transparent 46%),
                    linear-gradient(225deg, rgba(245, 158, 11, 0.13), transparent 44%),
                    var(--nexus-surface);
                box-shadow: var(--nexus-shadow);
                padding: 1.5rem;
                margin: 0.5rem 0 1rem 0;
            }}

            .nexus-eyebrow {{
                color: var(--nexus-accent);
                font-size: 0.78rem;
                font-weight: 800;
                letter-spacing: 0;
                text-transform: uppercase;
                margin-bottom: 0.4rem;
            }}

            .nexus-hero h2 {{
                margin: 0;
                font-size: 2rem;
                line-height: 1.1;
            }}

            .nexus-hero p {{
                max-width: 820px;
                color: var(--nexus-text-soft);
                margin: 0.75rem 0 0 0;
                line-height: 1.6;
            }}

            .nexus-kpi-row,
            .nexus-feature-grid {{
                display: grid;
                gap: 0.75rem;
            }}

            .nexus-kpi-row {{
                grid-template-columns: repeat(4, minmax(0, 1fr));
                margin: 1rem 0;
            }}

            .nexus-feature-grid {{
                grid-template-columns: repeat(3, minmax(0, 1fr));
                margin: 1rem 0 1.25rem 0;
            }}

            .nexus-kpi,
            .nexus-feature {{
                border: 1px solid var(--nexus-border);
                border-radius: var(--nexus-radius);
                background: var(--nexus-surface);
                padding: 1rem;
                min-height: 118px;
                box-shadow: var(--nexus-shadow);
            }}

            .nexus-kpi strong,
            .nexus-feature strong {{
                color: var(--nexus-text);
                display: block;
                font-size: 1rem;
                margin-bottom: 0.35rem;
            }}

            .nexus-kpi span,
            .nexus-feature span {{
                color: var(--nexus-text-soft);
                line-height: 1.5;
            }}

            .nexus-kpi:nth-child(2),
            .nexus-feature:nth-child(2) {{
                border-left: 4px solid var(--nexus-accent-2);
            }}

            .nexus-kpi:nth-child(3),
            .nexus-feature:nth-child(3) {{
                border-left: 4px solid var(--nexus-accent-3);
            }}

            .nexus-kpi:nth-child(1),
            .nexus-kpi:nth-child(4),
            .nexus-feature:nth-child(1),
            .nexus-feature:nth-child(4),
            .nexus-feature:nth-child(5),
            .nexus-feature:nth-child(6) {{
                border-left: 4px solid var(--nexus-accent);
            }}

            @media (max-width: 920px) {{
                .nexus-kpi-row,
                .nexus-feature-grid {{
                    grid-template-columns: 1fr;
                }}
                .nexus-hero {{
                    padding: 1rem;
                }}
                .nexus-hero h2 {{
                    font-size: 1.5rem;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

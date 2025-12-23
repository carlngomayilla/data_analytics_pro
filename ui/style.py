# ui/style.py
import streamlit as st

def style_css(theme):
    if theme == "dark":
        st.markdown("""
        <style>
            .stApp {background-color: #0e1117; color: #fafafa;}
            section[data-testid="stSidebar"] {background-color: #262730;}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            .stApp {background-color: #ffffff; color: #000000;}
            section[data-testid="stSidebar"] {background-color: #f0f2f6;}
        </style>
        """, unsafe_allow_html=True)
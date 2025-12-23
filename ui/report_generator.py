# ui/report_generator.py
import streamlit as st
from weasyprint import HTML
import plotly.io as pio
import pandas as pd
import base64

def generate_pdf(df: pd.DataFrame, figures: list, title: str):
    html = f"<h1>{title}</h1><table>{df.to_html()}</table>"
    for fig in figures:
        img = pio.to_image(fig, format='png')
        b64 = base64.b64encode(img).decode()
        html += f'<img src="data:image/png;base64,{b64}" />'
    
    pdf = HTML(string=html).write_pdf()
    return pdf
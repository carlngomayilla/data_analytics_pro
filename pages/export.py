# pages/export.py
import base64
import os
from datetime import datetime
from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st


def _get_weasyprint_html():
    try:
        from weasyprint import HTML
    except Exception as exc:
        return None, exc
    return HTML, None


def generate_graph_images(df):
    images = {}
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if len(numeric_cols) >= 2:
        fig = px.imshow(df[numeric_cols].corr(), text_auto=".2f", color_continuous_scale="RdBu_r")
        images["correlation"] = base64.b64encode(
            pio.to_image(fig, format="png", width=900, height=600)
        ).decode()

        fig = px.scatter(
            df,
            x=numeric_cols[0],
            y=numeric_cols[1],
            title=f"{numeric_cols[1]} vs {numeric_cols[0]}",
        )
        images["scatter"] = base64.b64encode(
            pio.to_image(fig, format="png", width=900, height=600)
        ).decode()

        fig = px.box(df, y=numeric_cols[0], title=f"Boite a moustaches de {numeric_cols[0]}")
        images["box"] = base64.b64encode(
            pio.to_image(fig, format="png", width=900, height=600)
        ).decode()

        fig = px.histogram(df, x=numeric_cols[0], nbins=50, title=f"Distribution de {numeric_cols[0]}")
        images["distribution"] = base64.b64encode(
            pio.to_image(fig, format="png", width=900, height=600)
        ).decode()

    return images


def generate_pdf_report(df):
    HTML, import_error = _get_weasyprint_html()
    if HTML is None:
        raise RuntimeError(f"WeasyPrint indisponible: {import_error}")

    images = generate_graph_images(df)

    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Data Analytics Pro - Rapport du {datetime.now().strftime('%d/%m/%Y')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }}
            h1 {{ color: #1e40af; text-align: center; }}
            h2 {{ color: #2563eb; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f0f9ff; }}
            img {{ max-width: 100%; height: auto; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1>Data Analytics Pro - Rapport d'analyse</h1>
        <p><strong>Date :</strong> {datetime.now().strftime('%d/%m/%Y a %H:%M')}</p>
        <p><strong>Donnees :</strong> {len(df):,} lignes x {len(df.columns)} colonnes</p>

        <h2>Statistiques</h2>
        {df.describe(include='all').to_html()}

        <h2>Apercu</h2>
        {df.head(20).to_html(index=False)}

        {f'<h2>Correlation</h2><img src="data:image/png;base64,{images.get("correlation")}">' if 'correlation' in images else ''}
        {f'<h2>Nuage de points</h2><img src="data:image/png;base64,{images.get("scatter")}">' if 'scatter' in images else ''}
        {f'<h2>Boite a moustaches</h2><img src="data:image/png;base64,{images.get("box")}">' if 'box' in images else ''}
        {f'<h2>Distribution</h2><img src="data:image/png;base64,{images.get("distribution")}">' if 'distribution' in images else ''}
    </body>
    </html>
    """

    pdf_file = f"rapport_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    HTML(string=html_content).write_pdf(pdf_file)
    return pdf_file


def generate_excel_report(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Donnees", index=False)
        df.describe(include="all").to_excel(writer, sheet_name="Statistiques")
        numeric = df.select_dtypes(include="number")
        if len(numeric.columns) >= 2:
            numeric.corr().to_excel(writer, sheet_name="Correlation")
    output.seek(0)
    return output.getvalue()


def main(df):
    st.title("Rapports et exports")

    if df is None:
        st.info("Chargez des donnees pour exporter un rapport.")
        return

    tab1, tab2 = st.tabs(["Rapport PDF", "Rapport Excel"])

    with tab1:
        html_cls, weasyprint_error = _get_weasyprint_html()
        pdf_enabled = html_cls is not None
        if not pdf_enabled:
            st.warning(
                "Export PDF indisponible sur cet environnement (bibliotheques systeme manquantes). "
                "L'export Excel reste disponible."
            )
            st.caption(f"Detail technique: {weasyprint_error}")

        if st.button("Generer le rapport PDF", disabled=not pdf_enabled):
            with st.spinner("Generation du rapport PDF..."):
                try:
                    pdf = generate_pdf_report(df)
                except Exception as exc:
                    st.error(f"Echec de generation PDF: {exc}")
                    pdf = None
            if pdf:
                with open(pdf, "rb") as f:
                    st.download_button(
                        "Telecharger le rapport PDF",
                        f,
                        file_name=os.path.basename(pdf),
                        mime="application/pdf",
                    )

    with tab2:
        if st.button("Generer le rapport Excel"):
            with st.spinner("Generation du rapport Excel..."):
                excel = generate_excel_report(df)
            st.download_button(
                "Telecharger le rapport Excel",
                excel,
                file_name=f"analyse_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


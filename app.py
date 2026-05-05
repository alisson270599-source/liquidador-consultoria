import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Liquidador de Consultoría", layout="wide")


# --- CLASE PARA EL PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 14)
        self.cell(0, 10, "REPORTE DE LIQUIDACIÓN DE CONTRATO", border=False, ln=1, align="C")
        self.ln(5)

    def chapter_title(self, title):
        self.set_font("helvetica", "B", 11)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, title, ln=1, fill=True)
        self.ln(2)


# --- INICIALIZACIÓN DE ESTADO ---
if "componentes" not in st.session_state:
    st.session_state.componentes = [
        {"nombre": "Componente 01", "n_entregables": 1}
    ]


# --- INTERFAZ PRINCIPAL ---
st.title("📑 Liquidación de Proyectos")
st.info("Basado en la estructura de: LIQUIDACION_CONSULTORIA_TEMPLATE.xlsx")


# 1. DATOS MAESTROS
with st.expander("⚙️ Configuración del Proyecto", expanded=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        entidad = st.text_input("Entidad", "Provías Nacional")
        consultor = st.text_input("Consultor", "Empresa de Ingeniería S.A.")

    with col2:
        monto_con_igv = st.number_input(
            "Monto Total Vigente del Contrato C/IGV",
            value=1791406.84,
            step=0.01,
            format="%.2f"
        )

        monto_sin_igv = monto_con_igv / 1.18

        # --- Estado inicial para adelanto ---
        if "pct_adelanto_ui" not in st.session_state:
            st.session_state.pct_adelanto_ui = 30.0
            st.session_state.slider_adelanto = 30.0
            st.session_state.input_adelanto = 30.0

        # --- Funciones de sincronización ---
        def sync_from_slider():
            valor = float(st.session_state.slider_adelanto)
            st.session_state.pct_adelanto_ui = valor
            st.session_state.input_adelanto = valor

        def sync_from_input():
            valor = float(st.session_state.input_adelanto)
            valor = max(0.0, min(30.0, valor))  # limita entre 0 y 30
            st.session_state.pct_adelanto_ui = valor
            st.session_state.slider_adelanto = valor
            st.session_state.input_adelanto = valor

        st.markdown("**% Adelanto Directo**")
        c_adel_1, c_adel_2 = st.columns([3, 1])

        with c_adel_1:
            st.slider(
                "Seleccione el porcentaje",
                min_value=0.0,
                max_value=30.0,
                step=0.01,
                key="slider_adelanto",
                on_change=sync_from_slider,
                label_visibility="collapsed"
            )

        with c_adel_2:
            st.number_input(
                "Ingrese manualmente",
                min_value=0.0,
                max_value=30.0,
                step=0.01,
                format="%.2f",
                key="input_adelanto",
                on_change=sync_from_input,
                label_visibility="collapsed"
            )

        pct_adelanto = st.session_state.pct_adelanto_ui / 100

    with col3:
        io = st.number_input("Índice Base Io", value=130.48, format="%.2f")
        ia = st.number_input("Índice Adelanto Ia", value=131.77, format="%.2f")


# 2. GESTIÓN DE COMPONENTES
st.subheader("🛠️ Estructura de Entregables")

if st.button("➕ Añadir Nuevo Componente"):
    st.session_state.componentes.append({
        "nombre": f"Componente {len(st.session_state.componentes) + 1}",
        "n_entregables": 1
    })

todos_entregables = []

for idx, comp in enumerate(st.session_state.componentes):
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 2, 1])

        comp["nombre"] = c1.text_input(
            "Nombre del Componente",
            comp["nombre"],
            key=f"name_{idx}"
        )

        comp["n_entregables"] = c2.number_input(
            "Cantidad de Entregables",
            min_value=1,
            value=comp["n_entregables"],
            key=f"n_{idx}"
        )

        if c3.button("🗑️", key=f"del_{idx}"):
            st.session_state.componentes.pop(idx)
            st.rerun()

        st.markdown("**Detalle de entregables**")

        for i in range(int(comp["n_entregables"])):
            cols = st.columns([3, 1, 1, 1, 1])

            desc = cols[0].text_input(
                "Descripción",
                f"Entregable {i + 1}",
                key=f"desc_{idx}_{i}"
            )

            peso = cols[1].number_input(
                "% Incidencia",
                value=10.0,
                step=0.01,
                format="%.2f",
                key=f"p_{idx}_{i}"
            ) / 100

            ir = cols[2].number_input(
                "Índice Ir",
                value=132.50,
                step=0.01,
                format="%.2f",
                key=f"ir_{idx}_{i}"
            )

            pagado_con_igv = cols[3].number_input(
                "Ya Pagado C/IGV",
                value=0.0,
                step=0.01,
                format="%.2f",
                key=f"pg_{idx}_{i}"
            )

            # --- CÁLCULOS ---
            monto_parcial_sin_igv = monto_sin_igv * peso

            reajuste = (ir / io - 1) * monto_parcial_sin_igv

            deduccion = ((ir - ia) / ia) * (monto_parcial_sin_igv * pct_adelanto)

            neto_sin_igv = monto_parcial_sin_igv + reajuste - deduccion

            neto_con_igv = neto_sin_igv * 1.18

            saldo = neto_con_igv - pagado_con_igv

            if saldo > 0:
                situacion = "Saldo por pagar"
            elif saldo < 0:
                situacion = "Saldo a favor de la entidad"
            else:
                situacion = "Cancelado"

            todos_entregables.append({
                "Componente": comp["nombre"],
                "Entregable": desc,
                "Monto S/IGV": round(monto_parcial_sin_igv, 2),
                "Ir": round(ir, 2),
                "Reajuste": round(reajuste, 2),
                "Deducción": round(deduccion, 2),
                "Neto S/IGV": round(neto_sin_igv, 2),
                "Neto C/IGV": round(neto_con_igv, 2),
                "Pagado C/IGV": round(pagado_con_igv, 2),
                "Saldo": round(saldo, 2),
                "Situación": situacion
            })


# 3. VISTA PREVIA Y EXPORTACIÓN
df = pd.DataFrame(todos_entregables)

if not df.empty:
    st.divider()
    st.subheader("📊 Resumen de Liquidación")

    st.dataframe(df, use_container_width=True)

    # --- TOTALES GENERALES ---
    total_valorizacion_sin_igv = df["Monto S/IGV"].sum()
    total_reajuste = df["Reajuste"].sum()
    total_deduccion = df["Deducción"].sum()

    subtotal_sin_igv = total_valorizacion_sin_igv + total_reajuste - total_deduccion
    igv = subtotal_sin_igv * 0.18
    total_liquidacion_con_igv = subtotal_sin_igv * 1.18

    total_pagado_con_igv = df["Pagado C/IGV"].sum()
    saldo_final = total_liquidacion_con_igv - total_pagado_con_igv

    if saldo_final > 0:
        estado_saldo = "SALDO A PAGAR AL CONSULTOR"
    elif saldo_final < 0:
        estado_saldo = "SALDO A FAVOR DE LA ENTIDAD"
    else:
        estado_saldo = "SIN SALDO PENDIENTE"

    # --- MÉTRICAS EN PANTALLA ---
    st.subheader("💰 Resultado financiero final")

    m1, m2, m3 = st.columns(3)

    m1.metric(
        "Total liquidación C/IGV",
        f"S/. {total_liquidacion_con_igv:,.2f}"
    )

    m2.metric(
        "Total pagado C/IGV",
        f"S/. {total_pagado_con_igv:,.2f}"
    )

    m3.metric(
        estado_saldo,
        f"S/. {abs(saldo_final):,.2f}"
    )

    # --- EXPORTAR A PDF ---
    if st.button("📝 Generar y Descargar PDF"):
        pdf = PDF(orientation="L", unit="mm", format="A4")
        pdf.add_page()

        # Datos generales
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 7, f"Entidad: {entidad}", ln=1)
        pdf.cell(0, 7, f"Consultor: {consultor}", ln=1)
        pdf.cell(0, 7, f"Fecha: {datetime.date.today()}", ln=1)
        pdf.ln(5)

        # Detalle por entregables
        pdf.chapter_title("1. DETALLE POR ENTREGABLES")

        pdf.set_font("helvetica", "B", 7)

        columnas_pdf = [
            "Componente",
            "Entregable",
            "Monto S/IGV",
            "Reaj.",
            "Ded.",
            "Neto C/IGV",
            "Pagado",
            "Saldo"
        ]

        anchos = [38, 50, 30, 26, 26, 32, 32, 32]

        for i, col in enumerate(columnas_pdf):
            pdf.cell(anchos[i], 8, col, 1, 0, "C")
        pdf.ln()

        pdf.set_font("helvetica", "", 7)

        for _, row in df.iterrows():
            pdf.cell(anchos[0], 6, str(row["Componente"])[:25], 1)
            pdf.cell(anchos[1], 6, str(row["Entregable"])[:35], 1)
            pdf.cell(anchos[2], 6, f"{row['Monto S/IGV']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[3], 6, f"{row['Reajuste']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[4], 6, f"{row['Deducción']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[5], 6, f"{row['Neto C/IGV']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[6], 6, f"{row['Pagado C/IGV']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[7], 6, f"{row['Saldo']:,.2f}", 1, 0, "R")
            pdf.ln()

        # Resumen financiero
        pdf.ln(8)
        pdf.chapter_title("2. RESUMEN FINANCIERO FINAL")

        pdf.set_font("helvetica", "", 10)

        resumen_data = [
            ("VALORIZACIÓN TOTAL SIN IGV", total_valorizacion_sin_igv),
            ("REAJUSTE TOTAL", total_reajuste),
            ("DEDUCCIONES TOTALES", total_deduccion),
            ("SUBTOTAL SIN IGV", subtotal_sin_igv),
            ("IGV 18%", igv),
            ("TOTAL LIQUIDACIÓN CON IGV", total_liquidacion_con_igv),
            ("TOTAL PAGADO CON IGV", total_pagado_con_igv),
            (estado_saldo, abs(saldo_final))
        ]

        for concepto, monto in resumen_data:
            if concepto == estado_saldo:
                pdf.set_font("helvetica", "B", 10)
            else:
                pdf.set_font("helvetica", "", 10)

            pdf.cell(120, 8, concepto, 1)
            pdf.cell(60, 8, f"S/. {monto:,.2f}", 1, 1, "R")

        # Interpretación final
        pdf.ln(6)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 8, "3. CONCLUSIÓN", ln=1)

        pdf.set_font("helvetica", "", 10)

        if saldo_final > 0:
            conclusion = (
                f"De la liquidación efectuada, se determina un saldo pendiente "
                f"por pagar al consultor ascendente a S/. {abs(saldo_final):,.2f}."
            )
        elif saldo_final < 0:
            conclusion = (
                f"De la liquidación efectuada, se determina un saldo a favor de la entidad "
                f"ascendente a S/. {abs(saldo_final):,.2f}."
            )
        else:
            conclusion = (
                "De la liquidación efectuada, no se determina saldo pendiente entre las partes."
            )

        pdf.multi_cell(0, 7, conclusion)

        pdf_name = "Liquidacion_Final.pdf"
        pdf.output(pdf_name)

        with open(pdf_name, "rb") as f:
            st.download_button(
                "📩 Descargar PDF de liquidación",
                f,
                file_name=pdf_name,
                mime="application/pdf"
            )

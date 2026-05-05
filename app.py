import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Liquidación de Proyectos", layout="wide")


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
        {"nombre": "Componente 1", "n_entregables": 1}
    ]

if "pct_adelanto_ui" not in st.session_state:
    st.session_state.pct_adelanto_ui = 30.0
    st.session_state.slider_adelanto = 30.0
    st.session_state.input_adelanto = 30.0


# --- FUNCIONES PARA SINCRONIZAR ADELANTO ---
def sync_from_slider():
    valor = float(st.session_state.slider_adelanto)
    st.session_state.pct_adelanto_ui = valor
    st.session_state.input_adelanto = valor


def sync_from_input():
    valor = float(st.session_state.input_adelanto)
    valor = max(0.0, min(30.0, valor))
    st.session_state.pct_adelanto_ui = valor
    st.session_state.slider_adelanto = valor
    st.session_state.input_adelanto = valor


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
            value=100000.00,
            step=0.01,
            format="%.2f"
        )

        monto_sin_igv = monto_con_igv / 1.18

        st.markdown("**% Adelanto Directo**")
        col_slider, col_manual = st.columns([3, 1])

        with col_slider:
            st.slider(
                "Seleccione el porcentaje de adelanto",
                min_value=0.0,
                max_value=30.0,
                step=0.01,
                key="slider_adelanto",
                on_change=sync_from_slider,
                label_visibility="collapsed"
            )

        with col_manual:
            st.number_input(
                "Ingrese manualmente el porcentaje de adelanto",
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
        io = st.number_input("Índice Base Io", value=130.50, step=0.01, format="%.2f")
        ia = st.number_input("Índice Adelanto Ia", value=131.77, step=0.01, format="%.2f")


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
        c1, c2, c3 = st.columns([3, 2, 0.2])

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
            cols = st.columns([3, 1, 1, 1])

            desc = cols[0].text_input(
                "Descripción",
                f"Entregable {i + 1}",
                key=f"desc_{idx}_{i}"
            )

            peso = cols[1].number_input(
                "% Incidencia",
                value=50.0,
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

            pago_efectuado_con_igv = cols[3].number_input(
                "Pago efectuado C/IGV",
                value=0.0,
                step=0.01,
                format="%.2f",
                key=f"pg_{idx}_{i}"
            )

            # --- CÁLCULOS BASE ---
            monto_parcial_sin_igv = monto_sin_igv * peso

            reajuste = (ir / io - 1) * monto_parcial_sin_igv

            # Deducción por reajuste del adelanto
            deduccion_reajuste_adelanto = ((ir - ia) / ia) * (monto_parcial_sin_igv * pct_adelanto)

            neto_sin_igv = monto_parcial_sin_igv + reajuste - deduccion_reajuste_adelanto
            neto_con_igv = neto_sin_igv * 1.18

            # Amortización del adelanto directo
            amortizacion_adelanto_con_igv = monto_con_igv * pct_adelanto * peso

            # Total reconocido al consultor:
            # pago efectuado + amortización del adelanto
            total_reconocido_con_igv = pago_efectuado_con_igv + amortizacion_adelanto_con_igv

            # Saldo real
            saldo = neto_con_igv - total_reconocido_con_igv

            if saldo > 0:
                situacion = "Saldo por pagar"
            elif saldo < 0:
                situacion = "Saldo a favor de la entidad"
            else:
                situacion = "Cancelado"

            todos_entregables.append({
                "Componente": comp["nombre"],
                "Entregable": desc,
                "% Incidencia": round(peso * 100, 2),
                "Monto S/IGV": round(monto_parcial_sin_igv, 2),
                "Ir": round(ir, 2),
                "Reajuste": round(reajuste, 2),
                "Deducción reajuste adelanto": round(deduccion_reajuste_adelanto, 2),
                "Neto S/IGV": round(neto_sin_igv, 2),
                "Neto C/IGV": round(neto_con_igv, 2),
                "Pago efectuado C/IGV": round(pago_efectuado_con_igv, 2),
                "Amortización adelanto C/IGV": round(amortizacion_adelanto_con_igv, 2),
                "Total reconocido C/IGV": round(total_reconocido_con_igv, 2),
                "Saldo": round(saldo, 2),
                "Situación": situacion
            })


# 3. VISTA PREVIA Y EXPORTACIÓN
df = pd.DataFrame(todos_entregables)

if not df.empty:
    st.divider()
    st.subheader("📊 Resumen de Liquidación")

    st.dataframe(df, use_container_width=True)

    # --- VALIDACIÓN DE INCIDENCIA ---
    total_incidencia = df["% Incidencia"].sum()

    if round(total_incidencia, 2) != 100.00:
        st.warning(
            f"⚠️ La suma de incidencias es {total_incidencia:.2f}%. "
            "Para una liquidación total del contrato, debería sumar 100%."
        )

    # --- TOTALES GENERALES ---
    total_valorizacion_sin_igv = df["Monto S/IGV"].sum()
    total_reajuste = df["Reajuste"].sum()
    total_deduccion_reajuste_adelanto = df["Deducción reajuste adelanto"].sum()

    subtotal_sin_igv = (
        total_valorizacion_sin_igv
        + total_reajuste
        - total_deduccion_reajuste_adelanto
    )

    igv = subtotal_sin_igv * 0.18
    total_liquidacion_con_igv = subtotal_sin_igv * 1.18

    total_pago_efectuado_con_igv = df["Pago efectuado C/IGV"].sum()
    total_amortizacion_adelanto_con_igv = df["Amortización adelanto C/IGV"].sum()
    total_reconocido_con_igv = df["Total reconocido C/IGV"].sum()

    saldo_final = total_liquidacion_con_igv - total_reconocido_con_igv

    if saldo_final > 0:
        estado_saldo = "SALDO A PAGAR AL CONSULTOR"
    elif saldo_final < 0:
        estado_saldo = "SALDO A FAVOR DE LA ENTIDAD"
    else:
        estado_saldo = "SIN SALDO PENDIENTE"

    # --- MÉTRICAS EN PANTALLA ---
    st.subheader("💰 Resultado financiero final")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Total liquidación C/IGV",
        f"S/. {total_liquidacion_con_igv:,.2f}"
    )

    m2.metric(
        "Pago efectuado C/IGV",
        f"S/. {total_pago_efectuado_con_igv:,.2f}"
    )

    m3.metric(
        "Amortización adelanto C/IGV",
        f"S/. {total_amortizacion_adelanto_con_igv:,.2f}"
    )

    m4.metric(
        estado_saldo,
        f"S/. {abs(saldo_final):,.2f}"
    )

    # --- EXPLICACIÓN EN PANTALLA ---
    with st.expander("📌 Ver explicación del cálculo del saldo"):
        st.write("El saldo final se calcula así:")
        st.code(
            "Saldo final = Total liquidación C/IGV - Pago efectuado C/IGV - Amortización del adelanto C/IGV",
            language="text"
        )

        st.write(f"Total liquidación C/IGV: S/. {total_liquidacion_con_igv:,.2f}")
        st.write(f"Pago efectuado C/IGV: S/. {total_pago_efectuado_con_igv:,.2f}")
        st.write(f"Amortización adelanto C/IGV: S/. {total_amortizacion_adelanto_con_igv:,.2f}")
        st.write(f"{estado_saldo}: S/. {abs(saldo_final):,.2f}")

    # --- EXPORTAR A PDF ---
    if st.button("📝 Generar y Descargar PDF"):
        pdf = PDF(orientation="L", unit="mm", format="A4")
        pdf.add_page()

        # Datos generales
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 7, f"Entidad: {entidad}", ln=1)
        pdf.cell(0, 7, f"Consultor: {consultor}", ln=1)
        pdf.cell(0, 7, f"Fecha: {datetime.date.today()}", ln=1)
        pdf.cell(0, 7, f"Monto contractual vigente C/IGV: S/. {monto_con_igv:,.2f}", ln=1)
        pdf.cell(0, 7, f"Adelanto directo: {st.session_state.pct_adelanto_ui:.2f}%", ln=1)
        pdf.ln(5)

        # Detalle por entregables
        pdf.chapter_title("1. DETALLE POR ENTREGABLES")

        pdf.set_font("helvetica", "B", 6)

        columnas_pdf = [
            "Componente",
            "Entregable",
            "Incid. %",
            "Monto S/IGV",
            "Reaj.",
            "Ded. reaj.",
            "Neto C/IGV",
            "Pago",
            "Amort.",
            "Reconoc.",
            "Saldo"
        ]

        anchos = [30, 38, 18, 25, 22, 24, 27, 27, 27, 27, 24]

        for i, col in enumerate(columnas_pdf):
            pdf.cell(anchos[i], 8, col, 1, 0, "C")
        pdf.ln()

        pdf.set_font("helvetica", "", 6)

        for _, row in df.iterrows():
            pdf.cell(anchos[0], 6, str(row["Componente"])[:22], 1)
            pdf.cell(anchos[1], 6, str(row["Entregable"])[:28], 1)
            pdf.cell(anchos[2], 6, f"{row['% Incidencia']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[3], 6, f"{row['Monto S/IGV']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[4], 6, f"{row['Reajuste']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[5], 6, f"{row['Deducción reajuste adelanto']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[6], 6, f"{row['Neto C/IGV']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[7], 6, f"{row['Pago efectuado C/IGV']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[8], 6, f"{row['Amortización adelanto C/IGV']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[9], 6, f"{row['Total reconocido C/IGV']:,.2f}", 1, 0, "R")
            pdf.cell(anchos[10], 6, f"{row['Saldo']:,.2f}", 1, 0, "R")
            pdf.ln()

        # Resumen financiero
        pdf.ln(8)
        pdf.chapter_title("2. RESUMEN FINANCIERO FINAL")

        pdf.set_font("helvetica", "", 10)

        resumen_data = [
            ("VALORIZACION TOTAL SIN IGV", total_valorizacion_sin_igv),
            ("REAJUSTE TOTAL", total_reajuste),
            ("DEDUCCION POR REAJUSTE DEL ADELANTO", total_deduccion_reajuste_adelanto),
            ("SUBTOTAL SIN IGV", subtotal_sin_igv),
            ("IGV 18%", igv),
            ("TOTAL LIQUIDACION CON IGV", total_liquidacion_con_igv),
            ("PAGO EFECTUADO CON IGV", total_pago_efectuado_con_igv),
            ("AMORTIZACION DEL ADELANTO CON IGV", total_amortizacion_adelanto_con_igv),
            ("TOTAL RECONOCIDO CON IGV", total_reconocido_con_igv),
            (estado_saldo, abs(saldo_final))
        ]

        for concepto, monto in resumen_data:
            if concepto == estado_saldo:
                pdf.set_font("helvetica", "B", 10)
            else:
                pdf.set_font("helvetica", "", 10)

            pdf.cell(130, 8, concepto, 1)
            pdf.cell(60, 8, f"S/. {monto:,.2f}", 1, 1, "R")

        # Conclusión final
        pdf.ln(6)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 8, "3. CONCLUSION", ln=1)

        pdf.set_font("helvetica", "", 10)

        if saldo_final > 0:
            conclusion = (
                f"De la liquidacion efectuada, considerando el pago efectuado y la "
                f"amortizacion del adelanto directo, se determina un saldo pendiente "
                f"por pagar al consultor ascendente a S/. {abs(saldo_final):,.2f}."
            )
        elif saldo_final < 0:
            conclusion = (
                f"De la liquidacion efectuada, considerando el pago efectuado y la "
                f"amortizacion del adelanto directo, se determina un saldo a favor de la entidad "
                f"ascendente a S/. {abs(saldo_final):,.2f}."
            )
        else:
            conclusion = (
                "De la liquidacion efectuada, considerando el pago efectuado y la "
                "amortizacion del adelanto directo, no se determina saldo pendiente entre las partes."
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

# app.py
import streamlit as st
import sqlglot
from PIL import Image 
from sqlglot import parse, errors
import re

st.set_page_config(page_title="Validador SQL", layout="wide")
imagen = Image.open("imagen/EKEKO.png")
# Crear columnas para centrar
col1, col2, col3 = st.columns([1,2,1])
# Mostrar imagen al medio
with col2:
    st.image(imagen, width=250)

st.title("🔍 DR QUERY - Tu QA Inteligente")
st.markdown("Carga un archivo `.sql` para validar lineamientos.")

uploaded_file = st.file_uploader(
    "Adjunta un archivo SQL",
    type=["sql"]
)
#tree.sqlglot.parse_one("select  a, b from tabla where x=1")
#print  (tree.sql(pretty=True))
# -----------------------------
# VALIDACIONES
# -----------------------------

SQL_KEYWORDS_CORRECTOS = {
    "SELEC": "SELECT",
    "FRM": "FROM",
    "INSER": "INSERT",
    "UPDAT": "UPDATE",
    "DELE": "DELETE",
    "WERE": "WHERE",
    "ODER": "ORDER"
}


def obtener_linea(script, texto):
    for i, line in enumerate(script.splitlines(), start=1):
        if texto.lower() in line.lower():
            return i, line.strip()
    return None, None


def agregar_hallazgo(lista, categoria, tipo, detalle, ubicacion):
    lista.append({
        "categoria": categoria,
        "tipo": tipo,
        "detalle": detalle,
        "ubicacion": ubicacion
    })


def validar_estructura(script, hallazgos):
    # Validar INSERT INTO estructura
    patron = r"INSERT\s+INTO\s+([A-Za-z0-9_]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+)"

    match = re.search(patron, script, re.IGNORECASE)

    #if not match:
    #    agregar_hallazgo(
    #        hallazgos,
    #        "Lineamientos de Estructura (Script)",
    #        "Alerta",
    #        "No se encontró estructura válida INSERT INTO BaseDeDatos.Catálogo.Esquema.Tabla",
    #        "INSERT INTO"
    #    )

    # Validar comandos mal escritos
    for incorrecto, correcto in SQL_KEYWORDS_CORRECTOS.items():
        patron_error = rf"\b{incorrecto}\b"

        for match in re.finditer(patron_error, script, re.IGNORECASE):
            linea_num = script[:match.start()].count("\n") + 1

            agregar_hallazgo(
                hallazgos,
                "Lineamientos de Estructura (Script)",
                "Error",
                f"Comando SQL mal escrito '{incorrecto}'. Quizás quiso decir '{correcto}'.",
                f"Línea {linea_num}"
            )


def validar_calidad(script, hallazgos):

    # SELECT *
    patron_select_all = r"SELECT\s+\*"

    for match in re.finditer(patron_select_all, script, re.IGNORECASE):
        linea_num = script[:match.start()].count("\n") + 1

        agregar_hallazgo(
            hallazgos,
            "Lineamientos de Calidad en Transformaciones",
            "CRITICO",
            "No se permite el uso de SELECT *.",
            f"Línea {linea_num}"
        )

    # DELETE sin WHERE
    patron_delete = r"DELETE\s+FROM\s+[A-Za-z0-9_\.]+\s*;"

    for match in re.finditer(patron_delete, script, re.IGNORECASE):
        linea_num = script[:match.start()].count("\n") + 1

        agregar_hallazgo(
            hallazgos,
            "Lineamientos de Calidad en Transformaciones",
            "CRITICO",
            "DELETE sin WHERE.",
            f"Línea {linea_num}"
        )

    # UPDATE sin WHERE
    patron_update = r"UPDATE\s+[A-Za-z0-9_\.]+\s+SET\s+.*?;"

    for match in re.finditer(patron_update, script, re.IGNORECASE | re.DOTALL):

        bloque = match.group(0)

        if "WHERE" not in bloque.upper():

            linea_num = script[:match.start()].count("\n") + 1

            agregar_hallazgo(
                hallazgos,
                "Lineamientos de Calidad en Transformaciones",
                "CRITICO",
                "UPDATE sin WHERE.",
                f"Línea {linea_num}"
            )

    # Transacción sin rollback
    if "BEGIN TRAN" in script.upper():
        if "ROLLBACK" not in script.upper():

            linea_num, _ = obtener_linea(script, "BEGIN TRAN")

            agregar_hallazgo(
                hallazgos,
                "Lineamientos de Calidad en Transformaciones",
                "CRITICO",
                "Transacción sin ROLLBACK.",
                f"Línea {linea_num}"
            )


def validar_arquitectura(script, hallazgos):

    # Procedimiento almacenado
    if re.search(r"CREATE\s+PROCEDURE", script, re.IGNORECASE):

        tiene_try = re.search(r"BEGIN\s+TRY", script, re.IGNORECASE)
        tiene_catch = re.search(r"BEGIN\s+CATCH", script, re.IGNORECASE)

        if not (tiene_try and tiene_catch):

            linea_num, _ = obtener_linea(script, "CREATE PROCEDURE")

            agregar_hallazgo(
                hallazgos,
                "Lineamientos de Consistencia de Arquitectura",
                "Error",
                "El procedimiento almacenado no tiene TRY/CATCH.",
                f"Línea {linea_num}"
            )


def validar_sqlglot(script, hallazgos):

    try:
        parse(script, read="tsql")

    except errors.ParseError as e:

        agregar_hallazgo(
            hallazgos,
            "Lineamientos de Estructura (Script)",
            "Error",
            f"Error de sintaxis SQL detectado por sqlglot: {str(e)}",
            "Sintaxis SQL"
        )


def mostrar_resultados(hallazgos):

    categorias = [
        "Lineamientos de Estructura (Script)",
        "Lineamientos de Consistencia de Arquitectura",
        "Lineamientos de Calidad en Transformaciones",
        "Lineamientos sobre Columnas"
    ]

    if hallazgos:
        st.markdown("## 🚨 Hallazgos (Errores y/o Alertas)")

    for categoria in categorias:

        st.markdown(f"{categoria}:")
        st.markdown("-------------------------")

        encontrados = [h for h in hallazgos if h["categoria"] == categoria]

        if encontrados:

            for h in encontrados:

                st.markdown(f"* **Tipo:** {h['tipo']}")
                st.markdown(f"* **Detalle:** {h['detalle']}")
                st.markdown(f"* **Ubicación:** {h['ubicacion']}")
                st.markdown("-------------------------")

        else:
            st.markdown("#### ✅ No se encontraron errores ni alertas.")
            st.markdown("-------------------------")


# -----------------------------
# MAIN
# -----------------------------

if uploaded_file:

    contenido = uploaded_file.read().decode("utf-8")

    st.subheader("Contenido SQL")
    st.code(contenido, language="sql")

    hallazgos = []

    validar_sqlglot(contenido, hallazgos)
    validar_estructura(contenido, hallazgos)
    validar_arquitectura(contenido, hallazgos)
    validar_calidad(contenido, hallazgos)

    mostrar_resultados(hallazgos)
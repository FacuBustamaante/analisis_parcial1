# ==========================================================
# Importaciones
# ==========================================================
# Path de pathlib permite construir rutas de forma compatible con
# cualquier sistema operativo (Windows, Linux, Mac) sin necesidad
# de concatenar strings manualmente con barras.
from pathlib import Path

# pandas es la libreria principal para manipulacion de datos tabulares.
# Nos da el tipo DataFrame, que es esencialmente una tabla con filas y columnas.
import pandas as pd

# streamlit convierte un script Python en una aplicacion web interactiva.
# Cada vez que el usuario mueve un slider o cambia un filtro, Streamlit
# re-ejecuta el script completo de arriba hacia abajo.
import streamlit as st


# ==========================================================
# 1) Configuracion general de la pagina
# ==========================================================
# Esta llamada DEBE ser la primera instruccion de Streamlit en el archivo;
# si se llama despues de cualquier otro st.* Streamlit lanza un error.
# - page_title: lo que aparece en la pestana del navegador.
# - page_icon:  el emoji o URL que aparece como favicon.
# - layout="wide": usa todo el ancho disponible de la pantalla en lugar
#   del modo centrado angosto que viene por defecto.
st.set_page_config(
    page_title="Student Performance Dashboard",
    page_icon="📊",
    layout="wide",
)


# ==========================================================
# 2) Definimos rutas y columnas esperadas
# ==========================================================
# __file__ es la ruta absoluta de este mismo archivo (main.py).
# .resolve() convierte rutas relativas o con symlinks en rutas absolutas reales.
# .parent sube un nivel en el arbol de directorios.
# BASE_DIR  -> carpeta "diferencial/"
# PROJECT_DIR -> carpeta padre "analisis_parcial1/"
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

# Buscamos primero el CSV procesado (tiene columnas derivadas como
# Engagement_Index) y, si no existe, caemos al CSV crudo original.
# El operador / en pathlib concatena segmentos de ruta de forma segura.
PROCESSED_DATA_PATH = PROJECT_DIR / "Student_performance_procesado.csv"
RAW_DATA_PATH = PROJECT_DIR / "Student_performance.csv"

# Lista de columnas que la app NECESITA para funcionar correctamente.
# Si el dataset no las tiene, la funcion validate_columns() detiene
# la ejecucion con un mensaje de error claro en lugar de crashear
# con un KeyError crudo mas adelante.
REQUIRED_COLUMNS = [
    "Age",
    "Gender",
    "Ethnicity_Name",
    "StudyTimeWeekly",
    "Absences",
    "Tutoring",
    "ParentalSupport",
    "Extracurricular",
    "Sports",
    "Music",
    "Volunteering",
    "GPA",
    "GradeClass",
]


# ==========================================================
# 3) Cargamos los datos una sola vez para que la app sea mas rapida
# ==========================================================
# @st.cache_data guarda el resultado de esta funcion en memoria.
# La primera vez se ejecuta normalmente; las siguientes veces Streamlit
# devuelve el DataFrame ya calculado sin volver a leer el disco.
# Esto es crucial porque Streamlit re-ejecuta el script ante cada
# interaccion del usuario, y leer un CSV grande en cada click seria lento.
@st.cache_data
def load_data() -> pd.DataFrame:
    """Carga el dataset procesado y, si no existe, usa el archivo crudo.

    La idea es que la app funcione aunque el archivo procesado no este disponible.
    """

    # Preferimos el CSV procesado porque ya tiene columnas derivadas
    # (StudyTime_Norm, Engagement_Index, Participation_Total) que usamos
    # en clean_data() y en los filtros.
    if PROCESSED_DATA_PATH.exists():
        df = pd.read_csv(PROCESSED_DATA_PATH)
    elif RAW_DATA_PATH.exists():
        # Fallback: el CSV crudo no tiene columnas derivadas, pero la app
        # las omite graciosamente gracias a los chequeos "if column in df.columns".
        df = pd.read_csv(RAW_DATA_PATH)
    else:
        # Si ninguno de los dos archivos existe, no tiene sentido continuar.
        # Lanzamos FileNotFoundError con un mensaje descriptivo; el bloque
        # try/except del flujo principal lo captura y muestra el error al usuario.
        raise FileNotFoundError(
            "No se encontro Student_performance_procesado.csv ni Student_performance.csv"
        )

    return df


def validate_columns(df: pd.DataFrame) -> None:
    """Verifica que existan las columnas necesarias para la app."""

    # List comprehension: construye una lista con los nombres de columnas
    # que estan en REQUIRED_COLUMNS pero NO estan en el DataFrame cargado.
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]

    if missing:
        # st.error() muestra un cuadro rojo con el mensaje.
        # st.stop() detiene la ejecucion del script inmediatamente,
        # evitando que el resto de la app intente usar columnas inexistentes.
        st.error(
            "Faltan columnas necesarias para construir la app: "
            + ", ".join(missing)
        )
        st.stop()


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura tipos correctos y quita filas duplicadas si las hubiera."""

    # Trabajamos sobre una copia para no modificar el DataFrame original
    # que esta guardado en cache. Modificar el objeto en cache corromperia
    # los datos para todas las re-ejecuciones futuras.
    df = df.copy()

    # Lista de columnas que deben ser numericas. Algunas pueden haber sido
    # leidas como texto si el CSV tenia valores mixtos o vacios.
    numeric_columns = [
        "Age",
        "Gender",
        "StudyTimeWeekly",
        "Absences",
        "Tutoring",
        "ParentalSupport",
        "Extracurricular",
        "Sports",
        "Music",
        "Volunteering",
        "GPA",
        "GradeClass",
        "StudyTime_Norm",      # solo existe en el CSV procesado
        "Engagement_Index",    # solo existe en el CSV procesado
        "Participation_Total", # solo existe en el CSV procesado
    ]

    for column in numeric_columns:
        if column in df.columns:
            # errors="coerce" convierte los valores que no se pueden
            # interpretar como numeros en NaN (Not a Number) en lugar
            # de lanzar una excepcion. Asi el DataFrame queda "limpio"
            # aunque el CSV tenga celdas con texto donde deberia haber numeros.
            df[column] = pd.to_numeric(df[column], errors="coerce")

    # Si existe una columna de ID unico, la usamos para deduplicar.
    # drop_duplicates conserva la primera aparicion de cada StudentID
    # y descarta las repetidas. Esto evita inflar promedios y conteos.
    if "StudentID" in df.columns:
        df = df.drop_duplicates(subset=["StudentID"])

    # Eliminamos filas donde alguna de las columnas clave sea NaN.
    # Sin esto, operaciones como .mean() o los sliders podrian fallar
    # o producir resultados engañosos con datos faltantes.
    df = df.dropna(subset=["Age", "StudyTimeWeekly", "Absences", "GPA"])

    return df


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Construye los filtros de la barra lateral y devuelve el dataframe filtrado."""

    # st.sidebar.* coloca los widgets en el panel lateral izquierdo de la app.
    st.sidebar.header("Filtros")
    st.sidebar.caption("Usa estos controles para explorar grupos especificos de estudiantes.")

    # --- Filtro 1: rango de edad ---
    # Calculamos el minimo y maximo reales del dataset para que el slider
    # cubra exactamente el rango disponible sin valores inalcanzables.
    age_min = int(df["Age"].min())
    age_max = int(df["Age"].max())
    # st.sidebar.slider con value=(min, max) crea un slider de dos extremos
    # (range slider) que devuelve una tupla (seleccionado_inf, seleccionado_sup).
    age_range = st.sidebar.slider("Rango de edad", age_min, age_max, (age_min, age_max))

    # --- Filtro 2: rango de GPA ---
    gpa_min = float(df["GPA"].min())
    gpa_max = float(df["GPA"].max())
    # round(..., 2) evita mostrar demasiados decimales en la etiqueta del slider.
    gpa_range = st.sidebar.slider(
        "Rango de GPA",
        min_value=round(gpa_min, 2),
        max_value=round(gpa_max, 2),
        value=(round(gpa_min, 2), round(gpa_max, 2)),
    )

    # --- Filtro 3: horas de estudio semanales ---
    study_min = float(df["StudyTimeWeekly"].min())
    study_max = float(df["StudyTimeWeekly"].max())
    study_range = st.sidebar.slider(
        "Horas de estudio semanales",
        min_value=round(study_min, 2),
        max_value=round(study_max, 2),
        value=(round(study_min, 2), round(study_max, 2)),
    )

    # --- Filtro 4: ausencias ---
    abs_min = int(df["Absences"].min())
    abs_max = int(df["Absences"].max())
    abs_range = st.sidebar.slider("Ausencias", abs_min, abs_max, (abs_min, abs_max))

    # --- Filtro 5: etnia ---
    # .dropna() descarta NaN antes de obtener los valores unicos, para que
    # "NaN" no aparezca como opcion en el multiselect.
    # .astype(str) garantiza que todos los valores sean texto (por si hay numeros).
    # sorted() ordena alfabeticamente para facilitar la busqueda visual.
    ethnicity_options = sorted(df["Ethnicity_Name"].dropna().astype(str).unique().tolist())
    # default=ethnicity_options selecciona TODAS las etnias por defecto,
    # es decir, no filtra nada al cargar la app.
    selected_ethnicities = st.sidebar.multiselect(
        "Etnia",
        options=ethnicity_options,
        default=ethnicity_options,
    )

    # --- Filtro 6: apoyo parental ---
    # ParentalSupport es un valor numerico ordinal (ej: 0, 1, 2, 3, 4).
    # Lo convertimos a int para que el multiselect muestre numeros enteros.
    parental_options = sorted(df["ParentalSupport"].dropna().astype(int).unique().tolist())
    selected_parental_support = st.sidebar.multiselect(
        "ParentalSupport",
        options=parental_options,
        default=parental_options,
    )

    # --- Filtro 7: GradeClass ---
    # GradeClass es la categoria final de nota (ej: 0.0 = A, 1.0 = B, etc.).
    # Usamos float para mantener consistencia con el tipo del DataFrame.
    grade_options = sorted(df["GradeClass"].dropna().astype(float).unique().tolist())
    selected_grade_class = st.sidebar.multiselect(
        "GradeClass",
        options=grade_options,
        default=grade_options,
    )

    # --- Filtro 8: participacion extracurricular ---
    # Un checkbox booleano; cuando esta activo solo se muestran estudiantes
    # cuya suma de actividades extracurriculares (Participation_Total) sea > 0.
    only_participating = st.sidebar.checkbox(
        "Solo estudiantes con alguna participacion extracurricular",
        value=False,  # desactivado por defecto para no ocultar datos al inicio
    )

    # --- Aplicacion de filtros ---
    # Encadenamos los filtros de forma secuencial sobre una copia del DataFrame.
    # Hacerlo paso a paso (en lugar de una sola expresion booleana gigante)
    # hace el codigo mas facil de leer y depurar.
    filtered_df = df.copy()

    # .between(a, b) es equivalente a (col >= a) & (col <= b), ambos inclusivos.
    filtered_df = filtered_df[filtered_df["Age"].between(age_range[0], age_range[1])]
    filtered_df = filtered_df[filtered_df["GPA"].between(gpa_range[0], gpa_range[1])]
    filtered_df = filtered_df[
        filtered_df["StudyTimeWeekly"].between(study_range[0], study_range[1])
    ]
    filtered_df = filtered_df[filtered_df["Absences"].between(abs_range[0], abs_range[1])]

    # Para los multiselect solo filtramos si el usuario dejo al menos una opcion
    # seleccionada. Si la lista esta vacia (desmarco todo), omitimos el filtro
    # para no devolver un DataFrame vacio de forma confusa.
    if selected_ethnicities:
        filtered_df = filtered_df[filtered_df["Ethnicity_Name"].astype(str).isin(selected_ethnicities)]

    if selected_parental_support:
        filtered_df = filtered_df[filtered_df["ParentalSupport"].isin(selected_parental_support)]

    if selected_grade_class:
        filtered_df = filtered_df[filtered_df["GradeClass"].isin(selected_grade_class)]

    # Solo aplicamos este filtro si la columna existe (viene del CSV procesado)
    # y si el usuario activo el checkbox.
    if only_participating and "Participation_Total" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Participation_Total"] > 0]

    return filtered_df


def render_kpi(label: str, value: str | int | float, help_text: str) -> None:
    """Muestra una tarjeta simple de metricas reutilizable."""

    # st.metric() genera una tarjeta visual con el titulo (label) y el valor.
    # El parametro help= muestra un icono de interrogacion con el texto de ayuda
    # al pasar el mouse, util para explicar que significa cada metrica.
    st.metric(label=label, value=value, help=help_text)


# ==========================================================
# 4) Cargamos, validamos y limpiamos la informacion
# ==========================================================
# Titulo principal visible al abrir la app en el navegador.
st.title("Dashboard de rendimiento estudiantil")
st.write(
    "Esta aplicacion permite explorar el rendimiento academico y los habitos de estudio "
    "a partir del dataset procesado de estudiantes."
)

# Intentamos cargar los datos. Si los archivos no existen, mostramos
# el error y detenemos la ejecucion con st.stop().
try:
    raw_df = load_data()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

# Verificamos que el DataFrame tenga todas las columnas necesarias.
# Si faltan columnas, validate_columns() llama a st.stop() internamente.
validate_columns(raw_df)

# Limpiamos tipos de datos y eliminamos duplicados/nulos.
# A partir de aqui trabajamos siempre con "df" (limpio) y no con "raw_df".
df = clean_data(raw_df)


# ==========================================================
# 5) Construimos la barra lateral de filtros
# ==========================================================
# apply_filters() dibuja los widgets en el sidebar Y devuelve el
# subconjunto del DataFrame que cumple todos los criterios seleccionados.
filtered_df = apply_filters(df)


# ==========================================================
# 6) Mostramos metricas generales en la parte superior
# ==========================================================
st.subheader("Resumen general")

# st.columns(4) divide el ancho de la pagina en 4 columnas iguales.
# Usamos unpacking directo para nombrar cada columna.
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    render_kpi(
        "Estudiantes",
        f"{len(filtered_df):,}",  # :, agrega separadores de miles (ej: 1,234)
        "Cantidad de filas luego de aplicar los filtros.",
    )

with metric_col2:
    # Condicion inline: si el DataFrame filtrado esta vacio mostramos "N/A"
    # para no obtener un error de .mean() sobre una serie vacia.
    render_kpi(
        "GPA promedio",
        f"{filtered_df['GPA'].mean():.2f}" if not filtered_df.empty else "N/A",
        "Promedio del rendimiento academico.",
    )

with metric_col3:
    render_kpi(
        "Horas de estudio promedio",
        f"{filtered_df['StudyTimeWeekly'].mean():.2f}" if not filtered_df.empty else "N/A",
        "Promedio de tiempo de estudio semanal.",
    )

with metric_col4:
    render_kpi(
        "Ausencias promedio",
        f"{filtered_df['Absences'].mean():.2f}" if not filtered_df.empty else "N/A",
        "Promedio de inasistencias en el grupo filtrado.",
    )


# ==========================================================
# 7) Agregamos mensajes rapidos de interpretacion
# ==========================================================
if not filtered_df.empty:
    # st.info() muestra un cuadro azul informativo con el resumen dinamico
    # que se actualiza cada vez que el usuario cambia los filtros.
    st.info(
        f"En este subconjunto, el GPA medio es {filtered_df['GPA'].mean():.2f} "
        f"y el promedio de ausencias es {filtered_df['Absences'].mean():.2f}."
    )
else:
    # st.warning() muestra un cuadro amarillo para advertir al usuario
    # que no hay datos con los filtros actuales.
    st.warning("No hay registros para los filtros seleccionados. Ajusta los controles de la barra lateral.")


# ==========================================================
# 8) Organizamos el analisis en pestañas para no saturar la pantalla
# ==========================================================
# st.tabs() crea pestañas navegables. Devuelve un context manager por cada
# pestana; el contenido dentro de "with tab_X:" solo se renderiza en esa pestana.
tab_resumen, tab_relaciones, tab_datos = st.tabs(
    ["Resumen", "Relaciones", "Datos filtrados"]
)


# ==========================================================
# 9) Pestaña de resumen: distribuciones y conteos basicos
# ==========================================================
with tab_resumen:

    # --- Histograma de GPA ---
    st.subheader("Distribucion de GPA")
    if not filtered_df.empty:
        # pd.cut() divide los valores de GPA en 10 intervalos iguales
        # (bins=10) y asigna a cada fila la etiqueta del intervalo al que pertenece.
        # Resultado: una Serie de categorias como "(2.5, 2.9]", "(2.9, 3.3]", etc.
        gpa_bins = pd.cut(filtered_df["GPA"], bins=10)

        gpa_distribution = (
            gpa_bins.astype(str)          # convertimos categorias a strings para poder operar
            .value_counts()               # cuenta cuantos alumnos caen en cada intervalo
            .reindex(                     # reindex reordena las filas segun el orden original
                sorted(gpa_bins.astype(str).unique()), fill_value=0
            )                             # fill_value=0 evita NaN en bins sin alumnos
            .rename_axis("Rango de GPA")  # nombra el indice para que el grafico lo muestre
            .reset_index(name="Cantidad") # convierte el indice en columna llamada "Cantidad"
        )
        # st.bar_chart espera un DataFrame con el indice como eje X y
        # la columna numerica como eje Y.
        st.bar_chart(gpa_distribution.set_index("Rango de GPA")["Cantidad"])
    else:
        st.info("No hay datos para mostrar la distribucion de GPA.")

    # --- Distribucion de GradeClass ---
    st.subheader("Distribucion de GradeClass")
    if not filtered_df.empty:
        grade_distribution = (
            filtered_df["GradeClass"]
            .value_counts()     # cuenta cuantos alumnos hay en cada categoria de nota
            .sort_index()       # ordena por el valor de la categoria (0, 1, 2, ...)
            .rename_axis("GradeClass")
            .reset_index(name="Cantidad")
        )
        st.bar_chart(grade_distribution.set_index("GradeClass"))
    else:
        st.info("No hay datos para mostrar GradeClass.")

    # --- GPA promedio por grupo etnico ---
    st.subheader("Promedio de GPA por etnia")
    if not filtered_df.empty:
        # groupby agrupa las filas por Ethnicity_Name y luego .mean()
        # calcula el promedio de GPA dentro de cada grupo.
        # as_index=False evita que Ethnicity_Name se convierta en indice,
        # dejando el DataFrame con columnas normales listo para set_index().
        gpa_by_ethnicity = filtered_df.groupby("Ethnicity_Name", as_index=False)["GPA"].mean()
        st.bar_chart(gpa_by_ethnicity.set_index("Ethnicity_Name"))
    else:
        st.info("No hay datos para agrupar por etnia.")


# ==========================================================
# 10) Pestaña de relaciones: exploramos variables numericas entre si
# ==========================================================
with tab_relaciones:
    # Dividimos la fila en dos columnas para mostrar dos graficos lado a lado.
    left_col, right_col = st.columns(2)

    with left_col:
        # Grafico de dispersion (scatter): cada punto es un alumno.
        # Eje X = horas de estudio semanales, Eje Y = GPA.
        # Una tendencia ascendente indicaria correlacion positiva entre estudio y nota.
        st.subheader("Horas de estudio vs GPA")
        if not filtered_df.empty:
            # .rename() cambia los nombres de columna solo para la visualizacion,
            # sin modificar el DataFrame subyacente.
            st.scatter_chart(filtered_df[["StudyTimeWeekly", "GPA"]].rename(
                columns={"StudyTimeWeekly": "Horas de estudio", "GPA": "GPA"}
            ))
        else:
            st.info("No hay datos para el grafico de dispersion.")

    with right_col:
        # Grafico de dispersion: Eje X = ausencias, Eje Y = GPA.
        # Una tendencia descendente indicaria que mas ausencias se asocian con menor GPA.
        st.subheader("Ausencias vs GPA")
        if not filtered_df.empty:
            st.scatter_chart(filtered_df[["Absences", "GPA"]].rename(
                columns={"Absences": "Ausencias", "GPA": "GPA"}
            ))
        else:
            st.info("No hay datos para el grafico de dispersion.")

    # --- Tabla de los 10 mejores alumnos por GPA ---
    st.subheader("Top 10 registros con mayor GPA")
    if not filtered_df.empty:
        # sort_values con ascending=False ordena de mayor a menor GPA.
        # .head(10) toma solo los primeros 10 resultados.
        top_gpa = filtered_df.sort_values("GPA", ascending=False).head(10)

        # Construimos dinamicamente la lista de columnas a mostrar:
        # solo incluimos las que existen en el DataFrame para que el codigo
        # funcione tanto con el CSV procesado como con el crudo.
        columns_to_show = [
            column
            for column in [
                "StudentID",
                "Age",
                "Gender",
                "Ethnicity_Name",
                "StudyTimeWeekly",
                "Absences",
                "ParentalSupport",
                "GPA",
                "GradeClass",
            ]
            if column in top_gpa.columns
        ]
        # use_container_width=True hace que la tabla ocupe todo el ancho disponible.
        st.dataframe(top_gpa[columns_to_show], use_container_width=True)
    else:
        st.info("No hay datos para ordenar por GPA.")


# ==========================================================
# 11) Pestaña de datos: tabla completa del subconjunto filtrado
# ==========================================================
with tab_datos:
    st.subheader("Datos filtrados")
    # Mostramos el DataFrame completo con todas sus columnas.
    # El usuario puede ordenar las columnas haciendo clic en el encabezado.
    st.dataframe(filtered_df, use_container_width=True)

    # Boton de descarga: convierte el DataFrame a CSV en memoria (no toca el disco),
    # lo codifica en UTF-8 y lo ofrece como descarga directa desde el navegador.
    # index=False excluye el indice numerico de pandas del archivo descargado.
    st.download_button(
        label="Descargar datos filtrados en CSV",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="student_performance_filtrado.csv",
        mime="text/csv",  # le dice al navegador que es un archivo CSV
    )


# ==========================================================
# 12) Cierre de la pagina con una nota de uso
# ==========================================================
# st.caption() muestra texto en letra pequena al pie de la pagina,
# ideal para notas secundarias que no merecen el espacio de un st.write().
st.caption(
    "Sugerencia: si quieres extender esta app, el siguiente paso natural es agregar "
    "una seccion predictiva para estimar GPA o GradeClass."
)

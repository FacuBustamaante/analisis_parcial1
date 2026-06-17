from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Student Performance Dashboard",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

PROCESSED_DATA_PATH = PROJECT_DIR / "Student_performance_procesado.csv"
RAW_DATA_PATH = PROJECT_DIR / "Student_performance.csv"

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


@st.cache_data
def load_data() -> pd.DataFrame:
    """Carga el dataset procesado y, si no existe, usa el archivo crudo.

    La idea es que la app funcione aunque el archivo procesado no este disponible.
    """

    if PROCESSED_DATA_PATH.exists():
        df = pd.read_csv(PROCESSED_DATA_PATH)
    elif RAW_DATA_PATH.exists():
        df = pd.read_csv(RAW_DATA_PATH)
    else:
        raise FileNotFoundError(
            "No se encontro Student_performance_procesado.csv ni Student_performance.csv"
        )

    return df


def validate_columns(df: pd.DataFrame) -> None:
    """Verifica que existan las columnas necesarias para la app."""

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]

    if missing:
        st.error(
            "Faltan columnas necesarias para construir la app: "
            + ", ".join(missing)
        )
        st.stop()


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura tipos correctos y quita filas duplicadas si las hubiera."""

    df = df.copy()

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
        "StudyTime_Norm",
        "Engagement_Index",
        "Participation_Total",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "StudentID" in df.columns:
        df = df.drop_duplicates(subset=["StudentID"])

    df = df.dropna(subset=["Age", "StudyTimeWeekly", "Absences", "GPA"])
    return df


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Construye los filtros de la barra lateral y devuelve el dataframe filtrado."""

    st.sidebar.header("Filtros")
    st.sidebar.caption("Usa estos controles para explorar grupos especificos de estudiantes.")
    age_min = int(df["Age"].min())
    age_max = int(df["Age"].max())
    age_range = st.sidebar.slider("Rango de edad", age_min, age_max, (age_min, age_max))
    gpa_min = float(df["GPA"].min())
    gpa_max = float(df["GPA"].max())

    gpa_range = st.sidebar.slider(
        "Rango de GPA",
        min_value=round(gpa_min, 2),
        max_value=round(gpa_max, 2),
        value=(round(gpa_min, 2), round(gpa_max, 2)),
    )

    study_min = float(df["StudyTimeWeekly"].min())
    study_max = float(df["StudyTimeWeekly"].max())
    study_range = st.sidebar.slider(
        "Horas de estudio semanales",
        min_value=round(study_min, 2),
        max_value=round(study_max, 2),
        value=(round(study_min, 2), round(study_max, 2)),
    )

    abs_min = int(df["Absences"].min())
    abs_max = int(df["Absences"].max())
    abs_range = st.sidebar.slider("Ausencias", abs_min, abs_max, (abs_min, abs_max))

    ethnicity_options = sorted(df["Ethnicity_Name"].dropna().astype(str).unique().tolist())

    selected_ethnicities = st.sidebar.multiselect(
        "Etnia",
        options=ethnicity_options,
        default=ethnicity_options,
    )

    parental_options = sorted(df["ParentalSupport"].dropna().astype(int).unique().tolist())
    selected_parental_support = st.sidebar.multiselect(
        "ParentalSupport",
        options=parental_options,
        default=parental_options,
    )

    grade_options = sorted(df["GradeClass"].dropna().astype(float).unique().tolist())
    selected_grade_class = st.sidebar.multiselect(
        "GradeClass",
        options=grade_options,
        default=grade_options,
    )

    only_participating = st.sidebar.checkbox(
        "Solo estudiantes con alguna participacion extracurricular",
        value=False,
    )

    filtered_df = df.copy()

    filtered_df = filtered_df[filtered_df["Age"].between(age_range[0], age_range[1])]
    filtered_df = filtered_df[filtered_df["GPA"].between(gpa_range[0], gpa_range[1])]
    filtered_df = filtered_df[
        filtered_df["StudyTimeWeekly"].between(study_range[0], study_range[1])
    ]
    filtered_df = filtered_df[filtered_df["Absences"].between(abs_range[0], abs_range[1])]

    if selected_ethnicities:
        filtered_df = filtered_df[filtered_df["Ethnicity_Name"].astype(str).isin(selected_ethnicities)]

    if selected_parental_support:
        filtered_df = filtered_df[filtered_df["ParentalSupport"].isin(selected_parental_support)]

    if selected_grade_class:
        filtered_df = filtered_df[filtered_df["GradeClass"].isin(selected_grade_class)]

    if only_participating and "Participation_Total" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Participation_Total"] > 0]

    return filtered_df


def render_kpi(label: str, value: str | int | float, help_text: str) -> None:
    """Muestra una tarjeta simple de metricas reutilizable."""
    st.metric(label=label, value=value, help=help_text)

st.title("Dashboard de rendimiento estudiantil")
st.write(
    "Esta aplicacion permite explorar el rendimiento academico y los habitos de estudio "
    "a partir del dataset procesado de estudiantes."
)

try:
    raw_df = load_data()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

validate_columns(raw_df)
df = clean_data(raw_df)
filtered_df = apply_filters(df)
st.subheader("Resumen general")
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    render_kpi(
        "Estudiantes",
        f"{len(filtered_df):,}",
        "Cantidad de filas luego de aplicar los filtros.",
    )

with metric_col2:
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

if not filtered_df.empty:
    st.info(
        f"En este subconjunto, el GPA medio es {filtered_df['GPA'].mean():.2f} "
        f"y el promedio de ausencias es {filtered_df['Absences'].mean():.2f}."
    )
else:
    st.warning("No hay registros para los filtros seleccionados. Ajusta los controles de la barra lateral.")

tab_resumen, tab_relaciones, tab_datos = st.tabs(
    ["Resumen", "Relaciones", "Datos filtrados"]
)

with tab_resumen:
    st.subheader("Distribucion de GPA")
    if not filtered_df.empty:
        gpa_bins = pd.cut(filtered_df["GPA"], bins=10)

        gpa_distribution = (
            gpa_bins.astype(str)
            .value_counts()
            .reindex(
                sorted(gpa_bins.astype(str).unique()), fill_value=0
            )
            .rename_axis("Rango de GPA")
            .reset_index(name="Cantidad")
        )

        st.bar_chart(gpa_distribution.set_index("Rango de GPA")["Cantidad"])
    else:
        st.info("No hay datos para mostrar la distribucion de GPA.")

    st.subheader("Distribucion de GradeClass")
    if not filtered_df.empty:
        grade_distribution = (
            filtered_df["GradeClass"]
            .value_counts()
            .sort_index()
            .rename_axis("GradeClass")
            .reset_index(name="Cantidad")
        )
        st.bar_chart(grade_distribution.set_index("GradeClass"))
    else:
        st.info("No hay datos para mostrar GradeClass.")

    st.subheader("Promedio de GPA por etnia")
    if not filtered_df.empty:
        gpa_by_ethnicity = filtered_df.groupby("Ethnicity_Name", as_index=False)["GPA"].mean()
        st.bar_chart(gpa_by_ethnicity.set_index("Ethnicity_Name"))
    else:
        st.info("No hay datos para agrupar por etnia.")

with tab_relaciones:
    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Horas de estudio vs GPA")
        if not filtered_df.empty:
            st.scatter_chart(filtered_df[["StudyTimeWeekly", "GPA"]].rename(
                columns={"StudyTimeWeekly": "Horas de estudio", "GPA": "GPA"}
            ))
        else:
            st.info("No hay datos para el grafico de dispersion.")

    with right_col:
        st.subheader("Ausencias vs GPA")
        if not filtered_df.empty:
            st.scatter_chart(filtered_df[["Absences", "GPA"]].rename(
                columns={"Absences": "Ausencias", "GPA": "GPA"}
            ))
        else:
            st.info("No hay datos para el grafico de dispersion.")

    st.subheader("Top 10 registros con mayor GPA")
    if not filtered_df.empty:
        top_gpa = filtered_df.sort_values("GPA", ascending=False).head(10)

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

        st.dataframe(top_gpa[columns_to_show], use_container_width=True)
    else:
        st.info("No hay datos para ordenar por GPA.")

with tab_datos:
    st.subheader("Datos filtrados")

    st.dataframe(filtered_df, use_container_width=True)

    st.download_button(
        label="Descargar datos filtrados en CSV",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="student_performance_filtrado.csv",
        mime="text/csv",
    )

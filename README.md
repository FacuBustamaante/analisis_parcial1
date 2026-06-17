# Análisis de Datos | Parcial 1

## Clonar el repositorio

```bash
git clone https://www.github.com/FacuBustamaante/analisis_parcial1
cd "Parcial 1"
```

## Crear el entorno virtual

En Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

## Ejecutar

Abrir y ejecutar cualquiera de los notebooks del proyecto, por ejemplo:

- `Hito 1.ipynb`
- `Hito 2.ipynb`

## Dashboard interactivo con Streamlit

El dashboard interactivo está en `Hito 4/main.py` y se levanta con Streamlit.

Con el entorno virtual activado e instaladas las dependencias, ejecutar:

```bash
streamlit run "Hito 4/main.py"
```

Esto inicia un servidor local y abre la app en el navegador. Si no se abre sola, ingresar manualmente a:

```
http://localhost:8501
```

Para detener el servidor, presionar `Ctrl + C` en la terminal.


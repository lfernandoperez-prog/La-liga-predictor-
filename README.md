# LaLiga Predictor — MVP personal

Prototipo experimental para analizar partidos de LaLiga con un CSV histórico. Funciona como web app adaptable al iPhone.

## Qué incluye
- Probabilidades 1X2.
- Más de 1,5 / 2,5 / 3,5 goles.
- Ambos equipos marcan.
- Cinco marcadores exactos con mayor probabilidad estimada.
- Medias de córners y tarjetas si el archivo trae esas columnas.
- Descarga del resumen de predicción.
- Filtro por fecha para evitar usar partidos posteriores al encuentro analizado.

## Requisitos
Python 3.10+ y conexión a internet para instalar paquetes.

## Ejecutar en ordenador
1. Descomprime el ZIP.
2. Abre una terminal dentro de la carpeta.
3. Ejecuta:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```
4. Se abrirá una dirección local en el navegador.
5. Sube un CSV histórico de LaLiga.

## Datos
Descarga manualmente un CSV desde:
- https://www.football-data.co.uk/spainm.php
- https://datahub.io/football/spanish-la-liga

Los archivos de Football-Data suelen tener columnas `Date`, `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`, `HC`, `AC`, `HY`, `AY`, `HR`, `AR`. La disponibilidad varía por temporada.

Lee y respeta los términos de cada proveedor:
https://www.football-data.co.uk/contact.php

No se descargan datos automáticamente. Para mejorar la cobertura histórica, puedes concatenar CSV de temporadas distintas siempre que sus columnas sean compatibles.

## Publicar para abrir desde el iPhone
1. Crea una cuenta en GitHub si no tienes.
2. Crea un repositorio y sube `app.py` y `requirements.txt`.
3. Abre https://share.streamlit.io/ e inicia sesión con GitHub.
4. Selecciona el repositorio, la rama y `app.py`; pulsa Deploy.
5. Abre la URL de Streamlit en Safari en el iPhone.
6. En Safari, pulsa Compartir → Añadir a pantalla de inicio.

Documentación oficial: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app

## Limitaciones importantes
- Este es un modelo de referencia, no un predictor profesional validado.
- Usa promedios ponderados y Poisson independiente; no modela lesiones, alineaciones, xG ni cambios tácticos.
- Las estadísticas de córners y tarjetas se muestran como medias descriptivas, no como probabilidades de mercado.
- El prototipo no trae partidos futuros automáticamente: primero hay que cargar un CSV.
- No garantiza aciertos ni beneficios. Evalúa el modelo fuera de muestra antes de confiar en sus estimaciones.

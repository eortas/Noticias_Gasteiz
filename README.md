# Gasteiz Live — Portal de Noticias con IA para Vitoria-Gasteiz

**Gasteiz Live** es un portal web de noticias local para Vitoria-Gasteiz y Álava, totalmente automatizado. Procesa noticias locales con inteligencia artificial y las publica en una web moderna con análisis de sentimiento, resumen diario y notificaciones en Telegram.

---

## ¿Qué hace?

### 1. Redacción automática de noticias
El sistema recopila noticias desde fuentes locales.

Las noticias nuevas se guardan en `data/news.json`. Para evitar duplicados, se mantiene un historial de URLs ya procesadas en `scraper/history.json`. Solo se conservan noticias de las últimas **72 horas**, con un máximo de **200 artículos**.

### 2. Deduplicación semántica
Tras el scraping, se ejecuta una deduplicación automática por título usando similitud de Jaccard. Cuando varias fuentes cubren la misma noticia, el sistema agrupa esos artículos en un único "cluster" sin eliminar ninguna versión, de forma que el usuario pueda elegir qué fuente prefiere leer.

### 3. Reescritura con IA 
Cada artículo nuevo se reescribe con inteligencia artificial usando el mejor modelo de Groq. El proceso es **paralelo** (hasta 6 hilos simultáneos) para mayor velocidad. La IA:
- Transforma el titular en una frase más directa e impactante.
- Reescribe el cuerpo con estilo narrativo propio, preservando todos los datos (nombres, cifras, fechas, proyectos).
- Guarda el texto original en los campos `original_title` y `original_body` por seguridad.

Los artículos reescritos se marcan con `"rewritten": true` para no volver a procesarse.

### 4. Análisis de sentimiento
Cada artículo recibe una puntuación de sentimiento (`positiva`, `negativa`, `neutral`) usando un sistema de dos capas:

1. **Heurístico**: diccionario de palabras positivas y negativas en español, con reglas especiales para ciertos temas.
2. **IA (Groq)**: si el heurístico devuelve `neutral`, se consulta al modelo de lenguaje para una clasificación más precisa junto con la categoría temática del artículo (Política, Economía, Sociedad, Deportes, Cultura, etc.).

### 5. Resumen diario generado por IA
Una vez al día, el sistema genera un resumen editorial de las noticias más importantes de Álava y Deportes usando Groq. El proceso es incremental:
- Si ya existe un resumen del día, detecta las noticias nuevas que aún no fueron incluidas y **amplía** el resumen existente.
- Si no existe resumen, genera uno completo desde cero.

El resumen tiene estructura periodística: titular atractivo, lead de apertura, desarrollo por temas y frase de cierre. Se inserta como el primer artículo del feed en `data/news.json`.

### 6. "Mood" de la ciudad
El script `update_mood.py` calcula diariamente el "estado de ánimo" medio de Vitoria-Gasteiz a partir del sentimiento de todas las noticias del día. El resultado (`score` entre -1 y +1) se guarda en `data/mood_history.json` con un historial de los últimos días.

### 7. Notificaciones en Telegram
El bot de Telegram envía automáticamente las noticias nuevas reescritas (de las secciones de Álava y Deportes) al canal configurado. Cada mensaje incluye:
- Titular en negrita.
- Extracto corto del cuerpo (máximo 250 caracteres).
- Enlace a `gasteizlive.vercel.app`.
- Imagen de la noticia si está disponible.

Se mantiene un registro en `data/sent_news_ids.json` para no reenviar noticias ya publicadas.


---

## El portal web

La web (`index.html` + `app.js` + `style.css`) es una aplicación de una sola página (SPA) sin frameworks, que se despliega en **Vercel** y se actualiza automáticamente con cada commit.

### Características de la interfaz

- **Feed de tarjetas**: muestra los artículos agrupados por clúster de noticias similares. Si una noticia ha sido cubierta por varias fuentes, aparece una etiqueta "N Fuentes" y un modal para elegir cuál leer.
- **Filtros de sentimiento**: contadores clicables de noticias Positivas, Neutrales, Negativas y Leídas. Al pulsar uno, el feed se filtra en tiempo real.
- **Secciones temáticas**: pestañas de Economía, Sociedad, Deportes y Cultura que filtran el feed por sección de origen.
- **Historial de leídas**: los artículos leídos se marcan en `localStorage` del navegador, aparecen con estilo atenuado y se desplazan al final del feed.
- **Vista de detalle**: al abrir una noticia se muestra la imagen en hero, el sentimiento, la fecha larga y el cuerpo completo. Si hay varias versiones de la misma noticia, aparecen botones para cambiar de fuente.
- **Widget de Mood**: barra animada con emoji que muestra el estado de ánimo de la ciudad ese día y un gráfico de barras de los últimos 7 días.
- **Tarjeta de resumen**: siempre visible en la parte superior del feed (sin filtro de sección activo), da acceso al resumen editorial del día generado por IA.
- **Botón atrás navegable**: compatible con el historial del navegador (botón atrás del sistema).

---

Made with ❤️ from Katowice for Vitoria-Gasteiz  

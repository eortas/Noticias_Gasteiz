# Gasteiz Live — Portal de Noticias con IA para Vitoria-Gasteiz

**Gasteiz Live** es un portal web de noticias local para Vitoria-Gasteiz y Álava, totalmente automatizado. Extrae noticias de varios medios locales, las procesa con inteligencia artificial y las publica en una web moderna con análisis de sentimiento, resumen diario y notificaciones en Telegram.

---

## ¿Qué hace?

### 1. Scraping automático de noticias
El sistema recopila noticias cada 5 minutos desde tres fuentes locales:

- **El Correo** (`elcorreo.com`): secciones de Álava, Economía, Sociedad, Deportes (Alavés y Baskonia) y Cultura. Para acceder al contenido completo de los artículos se usa un User-Agent de Googlebot.
- **Gasteiz Hoy** (`gasteizhoy.com`): a través de la API de WordPress, RSS y scraping de portada. Se filtra automáticamente contenido patrocinado y publirreportajes.
- **Diario de Noticias de Álava**: scraping directo con extracción de cuerpo del artículo e imagen.

Las noticias nuevas se guardan en `data/news.json`. Para evitar duplicados, se mantiene un historial de URLs ya procesadas en `scraper/history.json`. Solo se conservan noticias de las últimas **72 horas**, con un máximo de **200 artículos**.

### 2. Deduplicación semántica
Tras el scraping, se ejecuta una deduplicación automática por título usando similitud de Jaccard. Cuando varias fuentes cubren la misma noticia, el sistema agrupa esos artículos en un único "cluster" sin eliminar ninguna versión, de forma que el usuario pueda elegir qué fuente prefiere leer.

### 3. Reescritura con IA (Groq / Llama 3.3 70B)
Cada artículo nuevo se reescribe con inteligencia artificial usando el modelo `llama-3.3-70b-versatile` de Groq. El proceso es **paralelo** (hasta 6 hilos simultáneos) para mayor velocidad. La IA:
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
- Extracto corto del cuerpo (máximo 250 caracteres) para incentivar la visita a la web.
- Enlace a `gasteizlive.vercel.app`.
- Imagen de la noticia si está disponible (enviada como foto con caption).

Se mantiene un registro en `data/sent_news_ids.json` para no reenviar noticias ya publicadas.

### 8. Pipeline de podcast (opcional / manual)
El script `podcast_pipeline.py` automatiza la creación de un podcast diario mediante Playwright:
1. Genera un archivo de texto con las noticias nuevas no incluidas en podcasts anteriores.
2. Sube el archivo a **NotebookLM** (Google) para generar un resumen de audio.
3. Descarga el audio generado.
4. Sube el episodio automáticamente a **Spotify for Podcasters** con título y descripción del día.

El historial de artículos ya usados en el podcast se guarda en `scraper/podcast_history.json`.

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

## Automatización (GitHub Actions)

El archivo `.github/workflows/scrape.yml` ejecuta el pipeline completo **cada 5 minutos** en un runner de GitHub (`ubuntu-latest`):

1. `multi_scraper.py` — Scraping y deduplicación.
2. `parallel_rewrite.py` — Reescritura con IA.
3. `update_mood.py` — Cálculo del mood diario.
4. `generate_summary.py` — Resumen editorial del día.
5. `update_podcast.py` — Actualización de metadatos del podcast.
6. `enviar_telegram.py` — Envío de noticias al canal de Telegram.
7. `fix_missing_images_ddg.py` — Reparación de artículos sin imagen.

Al final, el bot hace un commit automático con los cambios en `data/news.json`, `data/mood_history.json`, `data/podcast.json` y otros archivos de datos, y hace push a `main`. Vercel detecta el push y redespliega la web automáticamente.

---

## Variables de entorno necesarias

El sistema necesita las siguientes variables de entorno (configuradas como Secrets en GitHub Actions):

| Variable | Uso |
|---|---|
| `GROQ_API_KEY` / `GROQ_REWRITE_KEY` / etc. | Pool de API keys de Groq para reescritura y análisis de sentimiento |
| `GROQ_RESUMEN` | API key de Groq específica para la generación del resumen diario |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram |
| `TELEGRAM_CHAT_ID` | ID del canal o grupo de Telegram destino |

---

## Estructura de datos

Cada artículo en `data/news.json` tiene los siguientes campos:

| Campo | Descripción |
|---|---|
| `id` | Hash MD5 de la URL (10 chars) |
| `title` | Titular reescrito por IA |
| `original_title` | Titular original de la fuente |
| `body` | Cuerpo reescrito por IA |
| `original_body` | Cuerpo original |
| `url` | URL del artículo original |
| `source` | Nombre del medio (`El Correo`, `Gasteiz Hoy`, `Diario de Noticias`) |
| `source_section` | Sección de origen (`alava`, `deportes`, `economia`, `sociedad`, `cultura`) |
| `category` | Categoría temática asignada por la IA |
| `date` | Fecha de publicación en ISO 8601 |
| `sentiment` | Puntuación numérica (-1 a 1) |
| `image` | URL de la imagen de portada |
| `rewritten` | `true` si fue procesado por la IA |
| `is_summary` | `true` si es el resumen diario |
| `telegram_sent` | `true` si ya fue enviado a Telegram |

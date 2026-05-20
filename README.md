# Vitoria Live • Portal de Noticias Inteligente con IA

Un portal de noticias de última generación para Vitoria-Gasteiz y Álava, automatizado y potenciado por Inteligencia Artificial para ofrecer una cobertura informativa curada, analítica y trilingüe.

---

## 🚀 Características Principales

### 📰 Fuentes Curadas e Identificación Visual
El portal recopila noticias de las principales cabeceras de la región, dándoles una identidad visual diferenciada mediante bordes degradados interactivos:
*   **El Correo (Álava):** Representado con un borde degradado premium en **Rojo y Negro** (`#ef4444` a `#000000`).
*   **Gasteiz Hoy:** Representado con un borde degradado dinámico en **Verde y Rojo** (`#22c55e` a `#ef4444`).
*   **Diario de Noticias de Álava (Álava + Vitoria-Gasteiz):** Representado con un borde degradado elegante en **Azul y Blanco** (`#3b82f6` a `#ffffff`).

### 🤖 Motor de Curación y Reescritura por IA (Groq Llama-3)
*   **Neutralidad Periodística:** Todas las noticias son reescritas automáticamente para eliminar firmas, sesgos explícitos y referencias directas a las fuentes de origen, proporcionando un estilo periodístico unificado.
*   **Filtrado Estricto de Patrocinados:** Exclusión automática de artículos promocionales, publirreportajes o que contengan leyendas de patrocinio como *"Contenido ofrecido por..."* o *"ofrecido por"*.
*   **Análisis de Sentimiento:** Clasificación inteligente de cada noticia en positiva, neutra o negativa.
*   **Vitoria "Mood":** Indicador dinámico que calcula y visualiza el "estado de ánimo" general de la ciudad basándose en el análisis agregado de las noticias de las últimas 24 horas.

### 🌐 Trilingüe Automático
Traducción integral en tiempo real a tres idiomas principales para una máxima accesibilidad:
*   🇪🇸 **Castellano**
*   🇪🇺 **Euskara (Basque)**
*   🇵🇱 **Polaco (Polish)**

### ⚡ Experiencia de Usuario Premium
*   **SPA Interactiva:** Aplicación de una sola página rápida, con preservación de scroll y animaciones fluidas.
*   **Feed Dinámico:** Lógica de visualización moderna donde las noticias ya leídas se desplazan automáticamente al final del feed para dar máxima prioridad al contenido nuevo y reciente.
*   **Diseño Oscuro Integrado:** Estética de alta fidelidad, adaptativa y optimizada para dispositivos móviles y de escritorio.

---

## 🛠️ Arquitectura Técnica

### Frontend
*   **Tecnologías:** Vanilla JavaScript, HTML5 semántico y CSS3 personalizado con variables y gradients modernos.
*   **Estrategia:** Renderizado del lado del cliente optimizado a partir del archivo estructurado `data/news.json`.

### Backend & Pipeline (Python)
*   **Multi-Scraper (`multi_scraper.py`):** Módulo encargado de parsear y extraer en paralelo el contenido, las imágenes dinámicas (usando DuckDuckGo Image API si no hay imagen principal) y los metadatos de las fuentes.
*   **Parallel Rewriter (`parallel_rewrite.py`):** Motor multihilo (6 workers concurrentes) que utiliza la API de Groq para procesar y reescribir con IA el contenido original a gran velocidad.
*   **Mood & Podcast Builder (`update_mood.py`, `update_podcast.py`):** Scripts que regeneran el histórico de sentimientos y estructuran el feed del podcast diario de noticias.
*   **Master Repair (`master_repair.py`):** Script de seguridad para garantizar que el 100% de los artículos tengan cubiertos todos sus campos de traducción y reescritura.

---

## 📦 Ejecución y Despliegue

### Requisitos Previos
1. Python 3.10+
2. Variables de entorno configuradas en un archivo `.env` en la raíz (ver `env.example`):
   ```env
   GROQ_API_KEY_1=tu_clave_1
   GROQ_API_KEY_2=tu_clave_2
   # ... hasta GROQ_API_KEY_6 para el balanceo y paralelismo
   ```

### Ejecutar el Pipeline Completo
Para actualizar el portal de forma manual y procesar todas las fuentes:
```bash
python run_pipeline.py
```

### Automatización (Windows Task Scheduler)
Para mantener el portal constantemente actualizado sin intervención, puedes programar la tarea automática cada 15 minutos en Windows:
```bash
schtasks /create /sc minute /mo 15 /tn "ActualizadorNoticiasGasteiz" /tr "C:\Ruta\Al\Proyecto\update_news_silent.bat" /it
```
*(Para más detalles sobre la automatización en Windows, consulta [INSTRUCCIONES_WINDOWS.md](file:///c:/Users/ortas/OneDrive/Documentos/Noticias_Gasteiz/INSTRUCCIONES_WINDOWS.md))*

---
*Desarrollado con ❤️ para Vitoria-Gasteiz y la comunidad de Álava.*

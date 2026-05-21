import os
import json
import time
import re
import unicodedata
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def clean_hashtag(text):
    """Normaliza un texto para usarlo como hashtag válido en Telegram."""
    if not text:
        return ""
    # Eliminar acentos y caracteres especiales
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Dejar solo caracteres alfanuméricos y capitalizar cada palabra (PascalCase)
    clean = re.sub(r'[^a-zA-Z0-9]', '', only_ascii.title())
    return f"#{clean}" if clean else ""

def sanitize_markdown(text):
    """Sanitiza el texto plano para evitar errores de parseo en Telegram Markdown."""
    if not text:
        return ""
    # En el parseo Markdown clásico de Telegram, los caracteres *, _, [ y ` tienen significado.
    # Los eliminamos o escapamos para que no rompan la estructura.
    text = text.replace("*", "")
    text = text.replace("[", "\\[")
    text = text.replace("`", "")
    # Escapar guiones bajos individuales
    text = text.replace("_", "\\_")
    return text

def truncate_body(body, max_allowed_len):
    """Trunca el cuerpo del texto para ajustarse al límite de caracteres de Telegram."""
    if len(body) <= max_allowed_len:
        return body
    truncated = body[:max_allowed_len - 3]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."

def format_message(title, body, url, category, source):
    """Formatea la noticia en Markdown con un resumen muy corto para incentivar la visita a la web."""
    # Sanitizar campos individuales
    clean_title = sanitize_markdown(title)
    
    # Encabezado, pie y enlaces (sin hashtags, enlace a la web general de gasteizlive)
    header = f"*【 {clean_title} 】*\n\n"
    footer = f"\n\n🔗 [Leer noticia completa](https://gasteizlive.vercel.app/)"
    
    # Límite corto para incentivar la visita a la web
    max_body_len = 250
        
    sanitized_body = sanitize_markdown(body)
    final_body = truncate_body(sanitized_body, max_body_len)
    
    return f"{header}{final_body}{footer}"

def send_telegram_message(token, chat_id, text, image_url=None):
    """Envía el mensaje a Telegram usando sendPhoto o sendMessage de respaldo."""
    # Intentar primero enviar foto si hay URL de imagen disponible
    if image_url:
        try:
            photo_url = f"https://api.telegram.org/bot{token}/sendPhoto"
            payload = {
                "chat_id": chat_id,
                "photo": image_url,
                "caption": text,
                "parse_mode": "Markdown"
            }
            print(f"Intentando enviar foto a Telegram: {image_url}")
            response = requests.post(photo_url, json=payload, timeout=15)
            if response.status_code == 200:
                print("Foto enviada con éxito a Telegram.")
                return True
            else:
                print(f"Error al enviar foto: Código {response.status_code}. Respuesta: {response.text}")
                print("Reintentando como mensaje de texto sin foto...")
        except Exception as e:
            print(f"Excepción al enviar foto a Telegram: {e}. Reintentando como texto...")

    # Fallback o envío directo como texto
    try:
        msg_url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        print("Enviando mensaje de texto a Telegram...")
        response = requests.post(msg_url, json=payload, timeout=15)
        if response.status_code == 200:
            print("Mensaje de texto enviado con éxito a Telegram.")
            return True
        else:
            print(f"Error al enviar mensaje de texto: Código {response.status_code}. Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"Excepción al enviar mensaje de texto a Telegram: {e}")
        return False

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("[WARNING] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados. Se omite el envío a Telegram.")
        return

    news_file = "data/news.json"
    if not os.path.exists(news_file):
        print(f"[ERROR] No se encontró el archivo de noticias: {news_file}")
        return

    try:
        with open(news_file, "r", encoding="utf-8") as f:
            news = json.load(f)
    except Exception as e:
        print(f"[ERROR] No se pudo leer el archivo de noticias: {e}")
        return

    # Buscar noticias que estén reescritas pero que no hayan sido enviadas a Telegram
    # Solo deben ser las de Alava:
    # - El Correo con sección "alava"
    # - Gasteiz Hoy (todas las noticias, ya que es de Vitoria/Álava)
    # - Diario de Noticias (todas las noticias, ya que es de Álava)
    candidates = []
    has_changes = False
    
    for item in news:
        if not item.get("rewritten"):
            continue
            
        if item.get("telegram_sent"):
            continue
            
        source = item.get("source", "")
        section = item.get("source_section", "")
        
        # Filtro de Álava
        is_alava = (
            (source == "El Correo" and section == "alava") or
            (source == "Gasteiz Hoy") or
            (source == "Diario de Noticias")
        )
        
        if is_alava:
            candidates.append(item)
        else:
            # Omitimos las noticias que no son de Álava para no volver a evaluarlas
            item["telegram_sent"] = "skipped"
            has_changes = True

    if not candidates:
        print("No hay noticias nuevas de Álava listas para enviar a Telegram.")
        if has_changes:
            try:
                with open(news_file, "w", encoding="utf-8") as f:
                    json.dump(news, f, indent=2, ensure_ascii=False)
                print(f"Archivo {news_file} actualizado. Se marcaron las noticias que no son de Álava como omitidas.")
            except Exception as e:
                print(f"[ERROR] No se pudo escribir en el archivo de noticias al omitir: {e}")
        return

    # Ordenar cronológicamente (más antiguas primero)
    candidates.sort(key=lambda x: x.get("date", ""))

    # Limitar envíos por ejecución para evitar spam
    MAX_SENDS_PER_RUN = 5
    to_send = candidates[:MAX_SENDS_PER_RUN]
    
    print(f"Detectadas {len(candidates)} noticias de Álava pendientes. Enviando un lote de {len(to_send)}...")

    sent_count = 0
    for item in to_send:
        title = item.get("title", "Noticia sin título")
        body = item.get("body", "")
        url = item.get("url", "")
        category = item.get("category", "General")
        source = item.get("source", "Noticias")
        image = item.get("image")

        message_text = format_message(title, body, url, category, source)
        
        success = send_telegram_message(token, chat_id, message_text, image_url=image)
        if success:
            item["telegram_sent"] = True
            sent_count += 1
            # Esperar 2 segundos para evitar límites de tasa del Bot de Telegram (30 msg/seg max a canales)
            time.sleep(2)
        else:
            print(f"Error procesando el envío de la noticia: {title}. Se reintentará en el próximo ciclo.")

    # Guardar cambios si enviamos alguna noticia o cambiamos estados a omitido
    if sent_count > 0 or has_changes:
        try:
            with open(news_file, "w", encoding="utf-8") as f:
                json.dump(news, f, indent=2, ensure_ascii=False)
            print(f"Archivo {news_file} actualizado. {sent_count} noticias enviadas, noticias no pertinentes omitidas.")
        except Exception as e:
            print(f"[ERROR] No se pudo escribir en el archivo de noticias: {e}")

if __name__ == "__main__":
    main()

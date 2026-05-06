from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import re

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(url_path.query)
        target_url = query.get('url', [None])[0]

        if not target_url:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Falta el parametro URL')
            return

        try:
            # SIMULACIÓN DE GOOGLEBOT
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            req = urllib.request.Request(target_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

            # Extraer Título
            title_match = re.search(r'<h1.*?>(.*?)</h1>', html, re.DOTALL)
            title = title_match.group(1) if title_match else "Noticia"
            title = re.sub('<.*?>', '', title).strip()

            # Extraer Párrafos y Limpiar
            p_matches = re.findall(r'<p.*?>(.*?)</p>', html, re.DOTALL)
            paragraphs = []
            blacklist = ["©", "todos los derechos reservados", "vídeo es exclusivo", "disfruta de acceso", "inicia sesión", "temas", "comentarios", "suscríbete"]
            
            for p in p_matches:
                text = re.sub('<.*?>', '', p).strip()
                if len(text) > 40 and not any(b.lower() in text.lower() for b in blacklist):
                    # Filtro de puntos finales
                    if not re.search(r'[.!?]$', text) and len(text.split()) < 20:
                        continue
                    paragraphs.append(text)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "title": title,
                "paragraphs": paragraphs
            }).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        return

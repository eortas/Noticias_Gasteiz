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
            is_elpais = 'elpais.com' in target_url.lower()
            
            headers_chrome = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
            }
            
            headers_googlebot = {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            
            # El Pais blocks Googlebot User-Agent with 403 unless verified.
            # We prefer Chrome headers directly for El Pais to avoid latency.
            if is_elpais:
                primary_headers, fallback_headers = headers_chrome, headers_googlebot
            else:
                primary_headers, fallback_headers = headers_googlebot, headers_chrome

            html = None
            try:
                req = urllib.request.Request(target_url, headers=primary_headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8', errors='ignore')
            except Exception as e:
                try:
                    req = urllib.request.Request(target_url, headers=fallback_headers)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        html = response.read().decode('utf-8', errors='ignore')
                except Exception as fallback_err:
                    raise Exception(f"Error fetching URL. Primary: {e}. Fallback: {fallback_err}")

            # Extraer Título
            title_match = re.search(r'<h1.*?>(.*?)</h1>', html, re.DOTALL)
            title = title_match.group(1) if title_match else "Noticia"
            title = re.sub('<.*?>', '', title).strip()

            # Extraer Párrafos y Limpiar (Soporte Vocento: El Correo, Diario Vasco)
            paragraphs = []
            
            # Intento 1: Extraer desde el JSON-LD (articleBody) que Googlebot recibe entero
            ld_jsons = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
            for ld in ld_jsons:
                try:
                    data = json.loads(ld)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'articleBody' in item:
                                paragraphs.extend(item['articleBody'].split('\n'))
                    elif isinstance(data, dict):
                        if 'articleBody' in data:
                            paragraphs.extend(data['articleBody'].split('\n'))
                except:
                    pass

            # Intento 2: Parsing HTML tradicional si no hay JSON-LD
            if not paragraphs:
                # Buscar tags con la clase específica de Vocento o <p> estándar
                p_matches = re.findall(r'<(?:p|div)[^>]*class="[^"]*voc-p[^"]*"[^>]*>(.*?)</(?:p|div)>', html, re.DOTALL)
                if not p_matches:
                    p_matches = re.findall(r'<p.*?>(.*?)</p>', html, re.DOTALL)
                
                blacklist = ["©", "todos los derechos reservados", "vídeo es exclusivo", "disfruta de acceso", "inicia sesión", "temas", "comentarios", "suscríbete", "iniciar sesión"]
                for p in p_matches:
                    text = re.sub('<.*?>', '', p).strip()
                    if len(text) > 40 and not any(b.lower() in text.lower() for b in blacklist):
                        if not re.search(r'[.!?]$', text) and len(text.split()) < 20:
                            continue
                        paragraphs.append(text)
            else:
                paragraphs = [re.sub('<.*?>', '', p).strip() for p in paragraphs if len(p.strip()) > 30]
            # Limpieza final y formateo (eliminar 'Noticia relacionada' y dividir textos largos)
            final_paragraphs = []
            junk_patterns = [r'Noticia relacionada.*?No\s*No', r'Noticia relacionada.*']
            
            for p in paragraphs:
                # Eliminar basura
                for junk in junk_patterns:
                    p = re.sub(junk, '', p, flags=re.IGNORECASE)
                
                p = p.strip()
                if not p:
                    continue
                
                # Dividir en oraciones (por cada punto, exclamación o interrogación)
                sentences = re.split(r'(?<=[.!?])\s+', p)
                chunk = []
                for s in sentences:
                    s = s.strip()
                    if s:
                        chunk.append(s)
                    # Cada 3 oraciones hacemos un salto de párrafo (o si es muy largo)
                    if len(chunk) >= 3:
                        final_paragraphs.append(' '.join(chunk))
                        chunk = []
                if chunk:
                    final_paragraphs.append(' '.join(chunk))

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "title": title,
                "paragraphs": final_paragraphs
            }).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        return

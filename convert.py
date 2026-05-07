import json
from datetime import datetime

def preparar_noticias_notebooklm(json_entrada, txt_salida):
    """
    Lee un JSON de noticias y genera un archivo de texto limpio 
    optimizado para subir a NotebookLM, filtrando solo las noticias de hoy.
    """
    with open(json_entrada, 'r', encoding='utf-8') as file:
        noticias = json.load(file)

    # Obtener la fecha actual en formato YYYY-MM-DD
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    with open(txt_salida, 'w', encoding='utf-8') as file:
        file.write(f"Documento de noticias del {fecha_hoy} recopiladas para generación de podcast.\n")
        file.write("=" * 60 + "\n\n")

        for noticia in noticias:
            fecha = noticia.get('date', '')[:10] # Extraer solo YYYY-MM-DD

            # Filtrar para procesar solo si la fecha coincide con la de hoy
            if fecha == fecha_hoy:
                titulo = noticia.get('title', 'Sin titular')
                categoria = noticia.get('category', 'General')
                cuerpo = noticia.get('body', 'Sin contenido')

                # Estructura clara para que la IA separe cada noticia
                file.write(f"SECCIÓN: {categoria.upper()}\n")
                file.write(f"FECHA: {fecha}\n")
                file.write(f"TITULAR: {titulo}\n")
                file.write(f"DESARROLLO:\n{cuerpo}\n")
                file.write("-" * 60 + "\n\n")

if __name__ == "__main__":
    ruta_input = 'news.json'
    ruta_output = 'noticias_hoy_notebooklm.txt'
    
    preparar_noticias_notebooklm(ruta_input, ruta_output)
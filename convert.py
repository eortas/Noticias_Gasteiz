import json
from datetime import datetime
from pathlib import Path

def preparar_noticias_notebooklm(json_entrada, txt_salida):
    """
    Lee un JSON de noticias y genera un archivo de texto limpio 
    optimizado para subir a NotebookLM, filtrando solo las noticias de hoy.
    """
    json_entrada = Path(json_entrada)
    txt_salida = Path(txt_salida)

    if not json_entrada.exists():
        raise FileNotFoundError(f"No se encontró el archivo de noticias: {json_entrada}")

    with json_entrada.open('r', encoding='utf-8') as file:
        noticias = json.load(file)

    # Obtener la fecha actual en formato YYYY-MM-DD
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    noticias_hoy = 0

    with txt_salida.open('w', encoding='utf-8') as file:
        file.write(f"Documento de noticias del {fecha_hoy} recopiladas para generación de podcast.\n")
        file.write("=" * 60 + "\n\n")

        for noticia in noticias:
            fecha = noticia.get('date', '')[:10] # Extraer solo YYYY-MM-DD

            # Filtrar para procesar solo si la fecha coincide con la de hoy
            if fecha == fecha_hoy:
                noticias_hoy += 1
                titulo = noticia.get('title', 'Sin titular')
                categoria = noticia.get('category', 'General')
                cuerpo = noticia.get('body', 'Sin contenido')

                # Estructura clara para que la IA separe cada noticia
                file.write(f"SECCIÓN: {categoria.upper()}\n")
                file.write(f"FECHA: {fecha}\n")
                file.write(f"TITULAR: {titulo}\n")
                file.write(f"DESARROLLO:\n{cuerpo}\n")
                file.write("-" * 60 + "\n\n")

    print(f"Generado {txt_salida} con {noticias_hoy} noticias del {fecha_hoy}.")

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    ruta_input = base_dir / 'data' / 'news.json'
    ruta_output = base_dir / 'noticias_hoy_notebooklm.txt'
    
    preparar_noticias_notebooklm(ruta_input, ruta_output)

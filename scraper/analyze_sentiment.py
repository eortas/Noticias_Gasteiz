import re

# Listas básicas de palabras para análisis de sentimiento en español
# (En un entorno real se usaría un modelo más complejo o una API)
PALABRAS_POSITIVAS = {
    'bueno', 'buena', 'mejor', 'excelente', 'positivo', 'éxito', 'logro', 'avanza', 'mejora', 
    'beneficio', 'alegría', 'feliz', 'oportunidad', 'crecimiento', 'esperanza', 'solución',
    'paz', 'seguro', 'impulsa', 'apoyo', 'vanguardia', 'moderno', 'eficiente', 'gratis',
    'estrena', 'inaugura', 'récord', 'lidera', 'brilla', 'talento', 'unión', 'solidario'
}

PALABRAS_NEGATIVAS = {
    'malo', 'mala', 'peor', 'negativo', 'fracaso', 'error', 'problema', 'crisis', 'daño', 
    'muerte', 'fallece', 'accidente', 'robo', 'detenido', 'agresión', 'pelea', 'herido',
    'denuncia', 'corte', 'huelga', 'protesta', 'incendio', 'atropello', 'crimen', 'estafa',
    'pérdida', 'caída', 'baja', 'tensión', 'riesgo', 'peligro', 'inseguro', 'sucio', 'abandono'
}

def analyze_sentiment(text):
    """
    Analiza el sentimiento de un texto en español de forma básica.
    Retorna 'positiva', 'negativa' o 'neutral' y un score numérico.
    """
    if not text:
        return 'neutral', 0.0
    
    # Tokenización simple y limpieza
    words = re.findall(r'\w+', text.lower())
    
    pos_count = sum(1 for w in words if w in PALABRAS_POSITIVAS)
    neg_count = sum(1 for w in words if w in PALABRAS_NEGATIVAS)
    
    total = pos_count + neg_count
    
    if total == 0:
        return 'neutral', 0.0
    
    score = (pos_count - neg_count) / total
    
    if score > 0.1:
        return 'positiva', score
    elif score < -0.1:
        return 'negativa', score
    else:
        return 'neutral', score

if __name__ == "__main__":
    # Test simple
    test_text = "El ayuntamiento inaugura un nuevo parque y mejora la vida de los vecinos con éxito."
    print(f"Test positivo: {analyze_sentiment(test_text)}")
    
    test_text_2 = "Fallece un hombre en un trágico accidente laboral en el polígono."
    print(f"Test negativo: {analyze_sentiment(test_text_2)}")

import os
import threading
import time

# Candado para garantizar que la rotación sea thread-safe en entornos multihilo
_lock = threading.Lock()

# Diccionario para almacenar el índice actual de cada pool de llaves
_key_indices = {}

def get_next_key(keys_list, pool_name="default"):
    """
    Obtiene la siguiente API key de la lista mediante rotación secuencial (Round-Robin).
    Filtra claves vacías o Nulas automáticamente y es seguro para ejecutarse con múltiples hilos.
    """
    valid_keys = [k for k in keys_list if k]
    if not valid_keys:
        return None
    
    with _lock:
        idx = _key_indices.get(pool_name, 0)
        selected_key = valid_keys[idx % len(valid_keys)]
        _key_indices[pool_name] = (idx + 1) % len(valid_keys)
        
    return selected_key

import os
import threading
import time

# Candado para garantizar que la rotación y el registro de enfriamiento sean seguros entre hilos
_lock = threading.Lock()

# Diccionario para almacenar el índice actual de cada pool de llaves
_key_indices = {}

# Diccionario para almacenar el tiempo límite de enfriamiento de claves con rate limit
_key_cooldowns = {}

def report_key_rate_limited(api_key, cooldown_seconds=25):
    """
    Registramos que una clave ha recibido un 429 (Rate Limit).
    La mantenemos en enfriamiento durante los segundos indicados para evitar reintentos inútiles.
    """
    if not api_key:
        return
    with _lock:
        _key_cooldowns[api_key] = time.time() + cooldown_seconds

def is_key_cooling(api_key):
    """
    Comprobamos si una clave está actualmente en periodo de enfriamiento.
    """
    if not api_key:
        return False
    with _lock:
        expire_time = _key_cooldowns.get(api_key, 0)
        return time.time() < expire_time

def get_next_key(keys_list, pool_name="default"):
    """
    Obtenemos la siguiente API key disponible de la lista.
    Priorizamos claves que no estén en enfriamiento por rate limit.
    Si todas están en enfriamiento, seleccionamos la que tenga menor tiempo de espera restante.
    """
    valid_keys = [k for k in keys_list if k]
    if not valid_keys:
        return None

    now = time.time()
    with _lock:
        # Filtramos claves que ya superaron su periodo de enfriamiento
        active_keys = [k for k in valid_keys if _key_cooldowns.get(k, 0) <= now]

        # Si tenemos claves listas sin rate limit, rotamos entre ellas
        if active_keys:
            idx = _key_indices.get(pool_name, 0)
            selected_key = active_keys[idx % len(active_keys)]
            _key_indices[pool_name] = (idx + 1) % len(active_keys)
            return selected_key

        # Si todas las claves están en enfriamiento, elegimos la que expire antes
        best_key = min(valid_keys, key=lambda k: _key_cooldowns.get(k, 0))
        return best_key


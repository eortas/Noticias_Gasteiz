import os
import requests

def cleanup_old_deployments():
    token = os.getenv("VERCEL_TOKEN")
    project_id = os.getenv("VERCEL_PROJECT_ID", "gasteizlive")
    team_id = os.getenv("VERCEL_TEAM_ID")

    if not token:
        print("[cleanup] VERCEL_TOKEN no configurado. Saltando limpieza.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    params = {"projectId": project_id, "limit": 100}
    if team_id:
        params["teamId"] = team_id

    url = "https://api.vercel.com/v6/deployments"
    
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            print(f"[cleanup] Error al listar despliegues ({res.status_code}): {res.text}")
            return

        deployments = res.json().get("deployments", [])
        print(f"[cleanup] Despliegues encontrados: {len(deployments)}")

        # Conservamos únicamente los 3 más recientes y borramos el resto
        to_delete = deployments[3:]
        deleted_count = 0

        for dep in to_delete:
            dep_id = dep.get("uid") or dep.get("id")
            del_url = f"https://api.vercel.com/v13/deployments/{dep_id}"
            del_params = {"teamId": team_id} if team_id else {}
            
            del_res = requests.delete(del_url, headers=headers, params=del_params)
            if del_res.status_code in (200, 204):
                deleted_count += 1
            else:
                print(f"[cleanup] No se pudo borrar {dep_id}: {del_res.status_code}")

        print(f"[cleanup] Limpieza completada. Despliegues eliminados: {deleted_count}")

    except Exception as e:
        print(f"[cleanup] Excepción durante la limpieza: {e}")

if __name__ == "__main__":
    cleanup_old_deployments()

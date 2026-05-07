import os
import sys
from fastapi import FastAPI, Request

# 1. Forzamos las rutas para que Python encuentre 'backend/app'
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, ".."))
backend_path = os.path.join(repo_root, "backend")

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 2. Intento de importación robusto
try:
    # Intentamos la ruta que Python debería ver gracias al sys.path
    from app.main import app as backend_app
except ImportError:
    try:
        # Intento de respaldo por si el entorno de Vercel prefiere ruta completa
        from backend.app.main import app as backend_app
    except ImportError as e:
        print(f"Error de importación: sys.path es {sys.path}")
        raise e

app = FastAPI()

# El wrapper que ya vimos para que el Login no tire 404
@app.api_route("/api/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def catch_all(request: Request, path_name: str):
    scope = request.scope.copy()
    scope['path'] = f"/{path_name}"
    return await backend_app(scope, request.receive, request.send)
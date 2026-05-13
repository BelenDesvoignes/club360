import os
import sys

# 1. Configuración de Paths (Correcto como lo tenías)
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, ".."))
backend_path = os.path.join(repo_root, "backend")

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 2. Importar la instancia original
from app.main import app as fastapi_app

# 3. Forzar el root_path aquí
# Esto asegura que FastAPI sepa que en producción vive detrás de /api
fastapi_app.root_path = "/api"

# 4. Exponer la app para Vercel
app = fastapi_app
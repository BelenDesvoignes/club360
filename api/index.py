import os
import sys

# Configuración de Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, ".."))
backend_path = os.path.join(repo_root, "backend")

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app as fastapi_app

# IMPORTANTE: Si tu Swagger local dice "Servers: /api", 
# entonces NO fuerces el root_path aquí, porque ya viene configurado en tu app.
app = fastapi_app
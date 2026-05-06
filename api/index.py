import os
import sys

# 1. Obtenemos la ruta absoluta de la carpeta donde está este archivo (api/)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Subimos un nivel para llegar a la raíz del proyecto
repo_root = os.path.abspath(os.path.join(current_dir, ".."))

# 3. Apuntamos a la carpeta 'backend'
backend_dir = os.path.join(repo_root, "backend")

# 4. Agregamos la carpeta 'backend' al sistema para que Python la vea primero
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 5. Ahora intentamos importar.
# Como agregamos 'backend' al sys.path, Python debería encontrar 'app/main.py' adentro.
try:
    from app.main import app as backend_app
except ImportError as e:
    # Si falla, imprimimos el path para debuguear en los logs de Vercel
    print(f"DEBUG: sys.path es {sys.path}")
    print(f"Error importando la app: {e}")
    raise e

# Exponemos la app para Vercel
app = backend_app
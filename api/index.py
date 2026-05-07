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

try:
    # Cambiamos la forma de importar para que sea más explícita
    import app.main
    backend_app = app.main.app
except ImportError as e:
    print(f"Error importando la app: {e}")
    # Si falla el anterior, probamos uno más por las dudas
    try:
        from backend.app.main import app as backend_app
    except ImportError:
        raise e

app = backend_app
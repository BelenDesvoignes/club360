from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.member import Member, Membership, Credit
from app.routes import auth


# 1. Crear la instancia de FastAPI
app = FastAPI(title="CLUB360 API")

app.add_middleware(# 2. Configuración de CORS
    CORSMiddleware,
    allow_origins=["*"], # Permite que cualquier frontend se conecte (ideal para desarrollo)
    allow_credentials=True,
    allow_methods=["*"], # Permite POST, GET, OPTIONS, etc.
    allow_headers=["*"], # Permite todos los headers
)

# 3. Endpoints (Tus rutas)
@app.get("/")
def home():
    return {"mensaje": "¡Bienvenido al backend de CLUB360!"}

# 4. Incluir las rutas con el prefijo /auth
# Esto hace que las rutas sean http://localhost:8000/auth/register
app.include_router(auth.router)

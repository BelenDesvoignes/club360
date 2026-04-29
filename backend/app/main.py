# Importamos la conexión
from app.database import engine, Base
# Importamos todos los modelos para que Base.metadata los reconozca
from app.models.user import User
from app.models.subscription import Subscription
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.attendance import Attendance
from app.models.suspension import Suspension
from app.models.credit import Credit
from app.routes import auth
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 1. Crear las tablas en la base de datos
# Esto buscará todas las clases que hereden de "Base" y las creará en Supabase
Base.metadata.create_all(bind=engine)

# 2. Instancia de FastAPI
app = FastAPI(title="CLUB360 API")

# 3. Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Rutas básicas
@app.get("/")
def home():
    return {"message": "Welcome to CLUB360 Backend!"}

# 5. Incluir Routers
app.include_router(auth.router)
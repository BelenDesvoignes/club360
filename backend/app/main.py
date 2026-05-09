# Importamos la conexión
from .database import engine, Base
# Importamos todos los modelos para que Base.metadata los reconozca
from .models.user import User
from .models.subscription import Subscription
from .models.booking import Booking
from .models.payment import Payment
from .models.attendance import Attendance
from .models.suspension import Suspension
from .models.credit import Credit
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, admin, activities, shifts, bookings, credits
from .models.activity import Activity           # Nueva
from .models.shift_template import ShiftTemplate # Nueva
from .models.shift_instance import ShiftInstance # Nueva
from .models.waiting_list import WaitingList


# 1. Instancia de FastAPI
app = FastAPI(title="CLUB360 API", root_path="/api")

# 2. Crear las tablas en la base de datos
# Esto buscará todas las clases que hereden de "Base" y las creará en Supabase
Base.metadata.create_all(bind=engine)

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
app.include_router(admin.router)
app.include_router(activities.router)
app.include_router(shifts.router)
app.include_router(bookings.router)
app.include_router(credits.router)
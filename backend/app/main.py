# Importamos la conexión
from .database import engine, Base
# Importamos todos los modelos para que Base.metadata los reconozca
from .models.user import User
from .models.card import Card
from .models.subscription import Subscription
from .models.booking import Booking
from .models.payment import Payment
from .models.attendance import Attendance
from .models.suspension import Suspension
from .models.credit import Credit
from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import date as date_type
from .routes import auth, admin, activities, shifts, bookings, credits, payments, cards, subscriptions, cron
from .models.activity import Activity           # Nueva
from .models.shift_template import ShiftTemplate # Nueva
from .models.shift_instance import ShiftInstance # Nueva
from .models.waiting_list import WaitingList
from .routes import dashboard
from .routes import waiting_lists
from .time_override import set_business_today_override, reset_business_today_override

# 1. Instancia de FastAPI
app = FastAPI(title="CLUB360 API", root_path="/api")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    for error in exc.errors():
        location = error.get("loc", [])
        field = location[-1] if location else ""

        if field == "email":
            return JSONResponse(
                status_code=422,
                content={"detail": "El correo electrónico no es válido. Revisá que no termine en punto o tenga espacios de más."},
            )

    return JSONResponse(
        status_code=422,
        content={"detail": "Revisá los datos ingresados porque hay campos que no son válidos."},
    )


@app.middleware("http")
async def business_day_override_middleware(request: Request, call_next):
    header_value = request.headers.get("x-club360-today")
    override_date = None
    if header_value:
        try:
            override_date = date_type.fromisoformat(header_value.strip())
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Header X-Club360-Today inválido. Usá formato YYYY-MM-DD."},
            )

    token = set_business_today_override(override_date)
    try:
        return await call_next(request)
    finally:
        reset_business_today_override(token)

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
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(cards.router)
app.include_router(subscriptions.router)
app.include_router(cron.router)
app.include_router(dashboard.router)
from .routes import attendances  # ← agregar al import
app.include_router(attendances.router)  # ← agregar junto a los otros
app.include_router(waiting_lists.router)

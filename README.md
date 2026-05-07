# club360
El proyecto CLUB360 consiste en la transformación digital de un centro de actividades deportivas. El sistema busca automatizar la gestión de turnos, cobros, asistencias y la comunicación con los socios.

## Cómo iniciar la app

### Primera vez
1. Abrí una terminal en la raíz del proyecto: `d:\club360`
2. Creá la virtualenv:
	- `python -m venv .venv`
3. Activá la virtualenv:
	- `.\.venv\Scripts\activate`
4. Instalá las dependencias del backend:
	- `pip install -r requirements.txt`
5. Instalá las dependencias del frontend:
	- `cd frontend`
	- `npm install`

### Cada vez que abras el proyecto
1. Abrí una terminal en la raíz del proyecto: `d:\club360`
2. Activá la virtualenv:
	- `.\.venv\Scripts\activate`
3. Levantá el backend:
	- `python -m uvicorn app.main:app --app-dir backend --reload --port 8000`
4. En otra terminal, levantá el frontend:
	- `cd frontend`
	- `npm run dev`

### URLs locales
- Backend: `http://127.0.0.1:8000`
- Frontend: la URL que muestre Vite, normalmente `http://127.0.0.1:5173`
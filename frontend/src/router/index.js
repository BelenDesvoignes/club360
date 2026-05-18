import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth' 
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import GestionEquipo from '../views/TeamManagement.vue'
import ActivityManagement from '../views/ActivityManagement.vue'
import ShiftsManagement from '../views/ShiftsManagement.vue'

// TUS IMPORTS (Mantenemos solo Pagos)
import UserPayments from '../views/UserPayments.vue'

// IMPORTS DE DEV (Lo que trajeron tus compañeros)
import MyBookings from '../views/MyBookings.vue'
import ClassBooking from '../views/ClassBooking.vue'
import AddCard from '../views/AddCard.vue'

// NUEVOS IMPORTS: Vistas del Empleado Administrativo

import ControlIngreso from '../views/ControlIngreso.vue'
import ControlAsistencias from '../views/ControlAsistencias.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/login', component: Login },
  { path: '/register', component: Register },

  // RUTAS DE SOCIO (Combinadas)
  { path: '/reservar', component: ClassBooking },
  { path: '/reservas', component: MyBookings, meta: { requiresAuth: true } },
  { path: '/agregar-tarjeta', component: AddCard, meta: { requiresAuth: true } },
  { 
    path: '/mis-pagos', 
    name: 'UserPayments',
    component: UserPayments, 
    meta: { requiresAuth: true } 
  },

  // RUTAS DE ADMINISTRADOR
  {
    path: '/clases',
    name: 'GestionClases',
    component: ShiftsManagement, 
    meta: { requiresAuth: true, role: 'admin' }
  },
  {
    path: '/equipo',
    name: 'GestionEquipo',
    component: GestionEquipo,
    meta: { requiresAuth: true, role: 'admin' }
  },
  {
    path: '/gestion-actividades',
    name: 'GestionActividades',
    component: ActivityManagement,
    meta: { requiresAuth: true, role: 'admin' }
  },

  // RUTAS EXCLUSIVAS PARA EL EMPLEADO ADMINISTRATIVO
  {
    path: '/control-ingreso',
    name: 'ControlIngreso',
    component: ControlIngreso,
    meta: { requiresAuth: true, role: 'empleado' } // El guard solo deja pasar si auth.role === 'employee'
  },
  {
    path: '/control-asistencias',
    name: 'ControlAsistencias',
    component: ControlAsistencias,
    meta: { requiresAuth: true, role: 'empleado' }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation Guard
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
  } else if (to.meta.role) {
    // Convertimos ambos a minúsculas...
    const userRole = String(auth.role || '').toLowerCase()
    const requiredRole = String(to.meta.role).toLowerCase()
    
    if (userRole !== requiredRole) {
      console.warn(`🛑 Acceso denegado. Rol del usuario: "${userRole}". Rol requerido: "${requiredRole}"`)
      next('/')
    } else {
      next()
    }
  } else {
    next()
  }
})
export default router
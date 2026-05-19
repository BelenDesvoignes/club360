import { createRouter, createWebHistory } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth' 
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import GestionEquipo from '../views/TeamManagement.vue'
import GestionClientes from '../views/ClientManagement.vue'
import ActivityManagement from '../views/ActivityManagement.vue'
import ShiftsManagement from '../views/ShiftsManagement.vue'

// TUS IMPORTS (Pagos)
import UserPayments from '../views/UserPayments.vue'

// IMPORTS DE DEV (Lo que trajeron tus compañeros)
import MyBookings from '../views/MyBookings.vue'
import ClassBooking from '../views/ClassBooking.vue'
import AddCard from '../views/AddCard.vue'

// NUEVOS IMPORTS: Vistas del Empleado Administrativo
import ControlIngreso from '../views/ControlIngreso.vue'
import ControlAsistencias from '../views/ControlAsistencias.vue'

const routes = [
  { path: '/', component: Home, meta: { headerTitle: 'CLUB360' } },
  { path: '/login', component: Login, meta: { headerTitle: 'Iniciar sesión' } },
  { path: '/register', component: Register, meta: { headerTitle: 'Crear cuenta' } },

  // RUTAS DE SOCIO (Combinadas)
  { path: '/reservar', component: ClassBooking, meta: { headerTitle: 'Reservar', headerSubtitle: 'Elegí deporte y tipo' } },
  { path: '/reservas', component: MyBookings, meta: { requiresAuth: true, headerTitle: 'Mis reservas' } },
  { path: '/agregar-tarjeta', component: AddCard, meta: { requiresAuth: true, headerTitle: 'Agregar tarjeta' } },
  { 
    path: '/mis-pagos', 
    name: 'UserPayments',
    component: UserPayments, 
    meta: { requiresAuth: true, headerTitle: 'Mis pagos' } 
  },

  // RUTAS DE ADMINISTRADOR
  {
    path: '/clases',
    name: 'GestionClases',
    component: ShiftsManagement, 
    meta: { requiresAuth: true, role: 'admin', headerTitle: 'Gestión de clases' }
  },
  {
    path: '/equipo',
    name: 'GestionEquipo',
    component: GestionEquipo,
    meta: { requiresAuth: true, role: 'admin', headerTitle: 'Equipo' }
  },
  {
    path: '/clientes',
    name: 'GestionClientes',
    component: GestionClientes,
    meta: { requiresAuth: true, role: ['admin', 'empleado'], headerTitle: 'Clientes' }
  },
  {
    path: '/gestion-actividades',
    name: 'GestionActividades',
    component: ActivityManagement,
    meta: { requiresAuth: true, role: 'admin', headerTitle: 'Actividades' }
  },

  // RUTAS EXCLUSIVAS PARA EL EMPLEADO ADMINISTRATIVO (CONSERVADAS)
  {
    path: '/control-ingreso',
    name: 'ControlIngreso',
    component: ControlIngreso,
    meta: { requiresAuth: true, role: ['admin', 'empleado'], headerTitle: 'Control QR' } 
  },
  {
    path: '/control-asistencias',
    name: 'ControlAsistencias',
    component: ControlAsistencias,
    meta: { requiresAuth: true, role: ['admin', 'empleado'], headerTitle: 'Cerrar Asistencias' }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Simple in-app navigation history (previous visited page)
export const previousRoutePath = ref(null)

// Navigation Guard Blindado
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  
  // 1. Control de Autenticación básica
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
    return
  }

  // 2. Control Avanzado de Roles (Soporta strings, arrays y minúsculas)
  if (to.meta.role) {
    const required = to.meta.role
    const userRole = String(auth.role || '').toLowerCase()
    
    // Si es una lista de roles permitidos (ej: ['admin', 'empleado'])
    if (Array.isArray(required)) {
      const hasRole = required.map(r => String(r).toLowerCase()).includes(userRole)
      if (!hasRole) {
        console.warn(`🛑 Acceso denegado. Rol del usuario: "${userRole}". Roles permitidos: ${required}`)
        next('/')
        return
      }
    } else {
      // Soporte para keyword especial 'employee' para dejar pasar empleado o admin
      if (required === 'employee') {
        if (!auth.isEmployee) {
          next('/')
          return
        }
      } else {
        // Validación estricta para rol único string plano
        const requiredRole = String(required).toLowerCase()
        if (userRole !== requiredRole) {
          next('/')
          return
        }
      }
    }
  }

  next()
})

router.afterEach((to, from) => {
  if (!from || !from.fullPath) return
  if (from.fullPath === to.fullPath) return
  previousRoutePath.value = from.fullPath
})

export default router
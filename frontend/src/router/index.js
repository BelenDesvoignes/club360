import { createRouter, createWebHistory } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth' 
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import GestionEquipo from '../views/TeamManagement.vue'
import GestionClientes from '../views/ClientManagement.vue'
import ActivityManagement from '../views/ActivityManagement.vue'
import ShiftsManagement from '../views/ShiftsManagement.vue' // <--- 1. IMPORTAR EL NUEVO


// TUS IMPORTS (Mantenemos solo Pagos)
import UserPayments from '../views/UserPayments.vue'

// IMPORTS DE DEV (Lo que trajeron tus compañeros)
import MyBookings from '../views/MyBookings.vue'
import ClassBooking from '../views/ClassBooking.vue'
import AddCard from '../views/AddCard.vue'

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
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Simple in-app navigation history (previous visited page)
export const previousRoutePath = ref(null)

// Navigation Guard
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
    return
  }

  if (to.meta.role) {
    const required = to.meta.role
    if (Array.isArray(required)) {
      if (!required.includes(auth.role)) {
        next('/')
        return
      }
    } else {
      // Support special keyword 'employee' to allow empleado OR admin
      if (required === 'employee') {
        if (!auth.isEmployee) {
          next('/')
          return
        }
      } else {
        if (auth.role !== required) {
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
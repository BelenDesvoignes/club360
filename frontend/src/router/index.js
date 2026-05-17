import { createRouter, createWebHistory } from 'vue-router'
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
    path: '/clientes',
    name: 'GestionClientes',
    component: GestionClientes,
    meta: { requiresAuth: true, role: ['admin', 'empleado'] }
  },
  {
    path: '/gestion-actividades',
    name: 'GestionActividades',
    component: ActivityManagement,
    meta: { requiresAuth: true, role: 'admin' }
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

export default router
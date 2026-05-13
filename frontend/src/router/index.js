import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import GestionEquipo from '../views/TeamManagement.vue'
import ActivityManagement from '../views/ActivityManagement.vue'
import ShiftsManagement from '../views/ShiftsManagement.vue' // <--- 1. IMPORTAR EL NUEVO
import MyBookings from '../views/MyBookings.vue'
import ClassBooking from '../views/ClassBooking.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  
  // Rutas de Usuario
  { path: '/reservar', component: ClassBooking },
  { path: '/reservas', component: MyBookings, meta: { requiresAuth: true } },

  // Rutas de Administrador
  {
    path: '/clases',
    name: 'GestionClases', // <--- 2. NOMBRE AGREGADO
    component: ShiftsManagement, // <--- 3. CAMBIAR EL TEMPLATE POR EL COMPONENTE REAL
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
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation Guard (Se mantiene igual, está perfecto)
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
  } else if (to.meta.role && auth.role !== to.meta.role) {
    next('/')
  } else {
    next()
  }
})

export default router
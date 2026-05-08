import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth' // Importante para la protección
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import GestionEquipo from '../views/TeamManagement.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  // Rutas protegidas (puedes crear estas vistas luego)
  { path: '/reservas', component: { template: '<div><h1>Mis Reservas</h1></div>' }, meta: { requiresAuth: true } },
  // Rutas protegidas - Solo Administradores
  {
    path: '/clases',
    component: { template: '<div><h1>Gestión de Clases</h1></div>' },
    meta: { requiresAuth: true, role: 'admin' }
  },
  {
    path: '/equipo',
    name: 'GestionEquipo',
    component: GestionEquipo,
    meta: { requiresAuth: true, role: 'admin' }
  }


]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation Guard: Protege las rutas
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  console.log("Ruta destino:", to.path)
  console.log("Rol requerido:", to.meta.role)
  console.log("Rol del usuario:", auth.role)

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
  } else if (to.meta.role && auth.role !== to.meta.role) {
    console.warn("Bloqueado por falta de permisos")
    next('/')
  } else {
    next()
  }
})

export default router
<template>
  <div>
    <button
      @click="isOpen = !isOpen"
      class="menu-toggle"
      :class="{ 'is-active': isOpen }"
    >
      <div class="bar"></div>
      <div class="bar"></div>
      <div class="bar"></div>
    </button>

    <div v-if="isOpen" class="overlay" @click="isOpen = false"></div>

    <aside :class="['sidebar', { 'is-open': isOpen }]">
      <div class="sidebar-header">
        <router-link to="/" @click="closeSidebar" class="logo-link">
          <h2 class="logo">CLUB<span>360</span></h2>
        </router-link>
      </div>

      <nav class="menu-content">
        
        <div v-if="auth.isAuthenticated && !auth.isAdmin && !auth.isEmployee" class="menu-section">
          <p class="section-title">MI CUENTA</p>
          <router-link to="/reservar" @click="closeSidebar">
            <span class="icon">📅</span> Reservar Clase
          </router-link>
          <router-link to="/reservas" @click="closeSidebar">
            <span class="icon">📋</span> Mis Reservas
          </router-link>
          <router-link to="/agregar-tarjeta" @click="closeSidebar">
            <span class="icon">💳</span> Mis Tarjetas
          </router-link>
          <router-link to="/mis-pagos" @click="closeSidebar">
            <span class="icon">💰</span> Mis Pagos
          </router-link>
        </div>

        <div v-if="auth.isEmployee" class="menu-section">
          <p class="section-title">OPERACIONES</p>
          <router-link to="/control-ingreso" @click="closeSidebar">
            <span class="icon">🔍</span> Control QR
          </router-link>
        </div>

        <div v-if="auth.isAdmin" class="menu-section">
          <p class="section-title">VISTA CLIENTE</p>
          <router-link to="/reservar" @click="closeSidebar">
            <span class="icon">📅</span> Reservar Clase
          </router-link>
          <router-link to="/reservas" @click="closeSidebar">
            <span class="icon">📋</span> Mis Reservas
          </router-link>
          <router-link to="/mis-pagos" @click="closeSidebar">
            <span class="icon">💰</span> Mis Pagos
          </router-link>
        </div>

        <div v-if="auth.isAdmin" class="menu-section">
          <p class="section-title">SISTEMA</p>
          <router-link to="/gestion-actividades" @click="closeSidebar">
             <span class="icon">⚙️</span> Gestión de Actividades
          </router-link>
          <router-link to="/clases" @click="closeSidebar">
             <span class="icon">⚙️</span> Gestión de Clases
          </router-link>
          <router-link to="/equipo" @click="closeSidebar">
            <span class="icon">👥</span> Gestión de Personal
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <button @click="handleLogout" class="logout-btn">
          <span class="icon">🚪</span> Cerrar Sesión
        </button>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const isOpen = ref(false)

const emit = defineEmits(['toggle'])

const closeSidebar = () => {
  isOpen.value = false
}

const handleLogout = () => {
  auth.logout()
  isOpen.value = false
  router.push('/login')
}

watch(isOpen, (val) => {
  emit('toggle', val)
})

onMounted(() => {
  emit('toggle', isOpen.value)
})
</script>

<style scoped>
/* Estilos del botón flotante */
.menu-toggle {
  position: fixed;
  top: 15px;
  left: 15px;
  z-index: 2000;
  background: #2d658d;
  border: none;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.menu-toggle.is-active {
  left: 210px;
  background: #ff6f00;
}

.bar { width: 22px; height: 2px; background: white; border-radius: 2px; }

/* Estilos de la Barra Lateral */
.sidebar {
  position: fixed;
  left: -280px;
  top: 0;
  width: 260px;
  height: 100vh;
  background: #ffffff;
  color: #111827;
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1500;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 25px rgba(0,0,0,0.1);
  border-right: 1px solid #e5e7eb;
}

.sidebar.is-open { left: 0; }

.sidebar-header {
  padding: 40px 20px 20px;
  background: #ffffff;
  display: flex;
  justify-content: center;
}

.logo-link { text-decoration: none; }

.logo {
  font-size: 1.5rem;
  margin: 0;
  font-weight: 900;
  color: #2d658d;
  letter-spacing: 2px;
}
.logo span { color: #ff6f00; } /* Naranja para el '360' */

.menu-content { flex-grow: 1; padding: 20px; overflow-y: auto; }
.menu-section { margin-bottom: 25px; }

.section-title {
  font-size: 0.7rem;
  color: #9ca3af;
  font-weight: 800;
  margin-bottom: 12px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
}

/* Links del Menú */
.sidebar a {
  display: flex;
  align-items: center;
  color: #374151;
  text-decoration: none;
  padding: 12px 15px;
  font-size: 0.9rem;
  font-weight: 600;
  border-radius: 10px;
  transition: all 0.2s;
  margin-bottom: 4px;
}

.sidebar a:hover {
  color: #2d658d;
  background: #f3f4f6;
  transform: translateX(5px);
}

.router-link-active {
  background: #f3f4f6;
  color: #ff6f00 !important;
}

.icon { margin-right: 12px; font-size: 1.1rem; }

/* Footer y Botón Logout */
.sidebar-footer {
  padding: 20px;
  border-top: 1px solid #f3f4f6;
}

.logout-btn {
  width: 100%;
  background: #ffffff;
  border: 1px solid #d1d5db;
  color: #4b5563;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 700;
  font-size: 0.85rem;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.logout-btn:hover {
  background: #fee2e2;
  color: #ef4444;
  border-color: #fecaca;
}

/* Overlay de fondo */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(45, 101, 141, 0.4);
  backdrop-filter: blur(3px);
  z-index: 1400;
}

@media (min-width: 1024px) {
  .overlay { display: none; }
}
</style>
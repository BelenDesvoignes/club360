<template>
  <div>
    <button
      v-if="auth.isAuthenticated"
      @click="toggleSidebar"
      class="menu-toggle"
      :class="{ 'is-active': isOpen }"
    >
      <div class="bar"></div>
      <div class="bar"></div>
      <div class="bar"></div>
    </button>

    <div v-if="isOpen" class="overlay" @click="toggleSidebar"></div>

    <aside :class="['sidebar', { 'is-open': isOpen }]">
      <div class="sidebar-header">
        <router-link to="/" @click="closeOnMobile" class="logo-link">
          <h2 class="logo">CLUB<span>360</span></h2>
        </router-link>

        <div class="user-badge" v-if="auth.isAuthenticated">
        </div>
      </div>

      <nav class="menu-content">


        <div v-if="auth.isEmployee" class="menu-section">
          <p class="section-title">OPERACIONES</p>
          <router-link to="/control-ingreso" @click="closeOnMobile">
            <span class="icon">🔍</span> Control de Ingreso (QR)
          </router-link>
          <router-link to="/clientes" @click="closeOnMobile">
            <span class="icon">👥</span> Gestión de Clientes
          </router-link>
        </div>

        <div v-if="auth.isAdmin" class="menu-section">
          <p class="section-title">ADMINISTRACIÓN</p>
          <router-link to="/clases" @click="closeOnMobile">
            <span class="icon">⚙️</span> Configurar Catálogo
          </router-link>
          <router-link to="/reportes" @click="closeOnMobile">
            <span class="icon">📊</span> Reportes y Auditoría
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <button @click="handleLogout" class="logout-btn">
          <span class="icon"</span> Cerrar Sesión
        </button>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const isOpen = ref(false)

const toggleSidebar = () => {
  isOpen.value = !isOpen.value
}

// Cierra la barra solo si estamos en resolución de celular/tablet
const closeOnMobile = () => {
  if (window.innerWidth < 1024) {
    isOpen.value = false
  }
}

const handleLogout = () => {
  auth.logout()
  isOpen.value = false
  router.push('/login')
}
</script>

<style scoped>
/* --- DISEÑO PARA MÓVILES (POR DEFECTO) --- */
.menu-toggle {
  position: fixed;
  top: 15px;
  left: 15px;
  z-index: 2000;
  background: #0d124a;
  border: none;
  width: 45px;
  height: 45px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 5px;
  transition: all 0.3s ease;
}

/* El botón se mueve con la barra cuando se abre */
.menu-toggle.is-active {
  left: 230px;
  background: #ff6f00;
}

.bar {
  width: 25px;
  height: 3px;
  background: white;
  border-radius: 2px;
}

.sidebar {
  position: fixed;
  left: -280px;
  top: 0;
  width: 280px;
  height: 100vh;
  background: #0d124a;
  color: white;
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1500;
  display: flex;
  flex-direction: column;
  box-shadow: 5px 0 15px rgba(0,0,0,0.3);
}

.sidebar.is-open {
  left: 0;
}

.sidebar-header {
  padding: 60px 20px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.logo-link {
  text-decoration: none;
  color: inherit;
  display: inline-block;
}

.logo {
  font-weight: 900;
  letter-spacing: 2px;
  margin: 0;
  font-size: 1.5rem;
  cursor: pointer;
}
.logo span { color: #ff6f00; }

.user-badge { margin-top: 15px; display: flex; flex-direction: column; }
.role {
  background: #ff6f00;
  font-size: 0.65rem;
  padding: 2px 8px;
  border-radius: 4px;
  width: fit-content;
  text-transform: uppercase;
  font-weight: bold;
}
.email { font-size: 0.8rem; color: #bdc3c7; margin-top: 5px; overflow: hidden; text-overflow: ellipsis; }

.menu-content { flex-grow: 1; padding: 20px; overflow-y: auto; }
.menu-section { margin-bottom: 25px; }
.section-title { color: #7f8c8d; font-size: 0.7rem; font-weight: bold; margin-bottom: 10px; letter-spacing: 1px; }

.sidebar a {
  display: flex;
  align-items: center;
  color: #ecf0f1;
  text-decoration: none;
  padding: 12px 0;
  font-size: 0.95rem;
  transition: 0.2s;
}
.sidebar a:hover { color: #ff6f00; }
.icon { margin-right: 12px; font-size: 1.1rem; }

.sidebar-footer { padding: 20px; border-top: 1px solid rgba(255,255,255,0.1); }
.logout-btn {
  width: 100%;
  background: rgba(231, 76, 60, 0.1);
  border: 1px solid #e74c3c;
  color: #e74c3c;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: 0.3s;
}
.logout-btn:hover { background: #e74c3c; color: white; }

.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 1400;
}

/* --- DISEÑO PARA PC (ESCRITORIO) --- */
@media (min-width: 1024px) {
  .sidebar {
    left: 0;
    width: 260px;
  }

  .menu-toggle, .overlay {
    display: none;
  }

  .sidebar-header {
    padding-top: 30px;
  }

  /* Si usas un layout con padding, este selector asegura que el contenido no se tape */
  :deep(.main-content) {
    margin-left: 260px;
    width: calc(100% - 260px);
  }
}
</style>
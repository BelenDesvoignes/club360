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


        <div v-if="auth.isEmployee" class="menu-section">
          <p class="section-title">OPERACIONES</p>
          <router-link to="/control-ingreso" @click="closeSidebar">
            <span class="icon"></span> Control QR
          </router-link>
          <router-link to="/clientes" @click="closeSidebar">
            <span class="icon"></span> Clientes
          </router-link>

        </div>
        <div v-if="auth.isAdmin" class="menu-section">
          <p class="section-title">SISTEMA</p>
          <router-link to="/gestion-actividades" @click="closeSidebar">
             <span class="icon"></span> Gestión de actividades
          </router-link>

          <router-link to="/equipo" @click="closeSidebar">
            <span class="icon"></span> Gestion de personal
          </router-link>
        </div>
      </nav>

      <div v-if="!auth.isAdmin && !auth.isEmployee && auth.isAuthenticated" class="menu-section">
  <p class="section-title">MI CUENTA</p>
  <router-link to="/mis-pagos" @click="closeSidebar">
    <span class="icon">💳</span> Mis Pagos
  </router-link>
</div>

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

// Definimos el evento para comunicarnos con App.vue
const emit = defineEmits(['toggle'])

// Cerramos y emitimos el cambio
const closeSidebar = () => {
  isOpen.value = false
}

const handleLogout = () => {
  auth.logout()
  isOpen.value = false
  router.push('/login')
}

// Avisamos a App.vue cada vez que isOpen cambie
watch(isOpen, (val) => {
  emit('toggle', val)
})

// Estado inicial al cargar
onMounted(() => {
  emit('toggle', isOpen.value)
})
</script>

<style scoped>
.menu-toggle {
  position: fixed;
  top: 15px;
  left: 15px;
  z-index: 2000;
  background: #0d124a;
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

.sidebar {
  position: fixed;
  left: -280px;
  top: 0;
  width: 260px;
  height: 100vh;
  background: #0d124a;
  color: white;
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1500;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 15px rgba(0,0,0,0.3);
}

.sidebar.is-open { left: 0; }

.sidebar-header { padding: 40px 20px 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }
.logo { font-size: 1.5rem; margin: 0; font-weight: 900; }
.logo span { color: #ff6f00; }

.user-badge { margin-top: 15px; }
.role { background: #ff6f00; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.65rem; text-transform: uppercase; }
.email { display: block; margin-top: 5px; opacity: 0.6; font-size: 0.75rem; word-break: break-all; }

.menu-content { flex-grow: 1; padding: 20px; overflow-y: auto; }
.menu-section { margin-bottom: 25px; }
.section-title { font-size: 0.65rem; color: #7f8c8d; font-weight: bold; margin-bottom: 12px; letter-spacing: 1px; }

.sidebar a {
  display: flex;
  align-items: center;
  color: #ecf0f1;
  text-decoration: none;
  padding: 12px 0;
  font-size: 0.95rem;
  transition: 0.2s;
}
.sidebar a:hover { color: #ff6f00; transform: translateX(5px); }
.icon { margin-right: 12px; }

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
}

.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 1400;
}

@media (min-width: 1024px) {
  .overlay { display: none; }
}
</style>
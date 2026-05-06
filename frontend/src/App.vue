<template>
  <div class="app-layout">
    <Sidebar v-if="auth.isAuthenticated" @toggle="handleSidebarToggle" />

    <main :class="['main-content', { 'full-width': !isSidebarOpen || !auth.isAuthenticated }]">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const isSidebarOpen = ref(false)

// Actualiza el estado local para expandir/contraer el contenido
const handleSidebarToggle = (state) => {
  isSidebarOpen.value = state
}
</script>

<style>
/* Estilos Globales */
body {
  margin: 0;
  padding: 0;
  font-family: 'Inter', sans-serif;
  background-color: #f8f9fa;
  overflow-x: hidden;
}

.app-layout {
  display: flex;
  min-height: 100vh;
  width: 100%;
}

.main-content {
  flex-grow: 1;
  width: 100%;
  /* Espacio reservado para la sidebar abierta */
  padding-left: 260px;
  transition: padding-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 100vh;
}

/* Clase para ocupar toda la pantalla */
.main-content.full-width {
  padding-left: 0;
}

/* En tablets y celulares, el contenido siempre es full width */
@media (max-width: 1024px) {
  .main-content {
    padding-left: 0 !important;
  }
}
</style>
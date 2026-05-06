<template>
  <div class="app-layout">
    <!-- Botón Hamburguesa (solo si está logueado) -->
    <button
      v-if="auth.isAuthenticated"
      @click="sidebarAbierta = !sidebarAbierta"
      class="menu-toggle"
    >
      <div class="bar"></div>
      <div class="bar"></div>
      <div class="bar"></div>
    </button>

    <Sidebar
      :isOpen="sidebarAbierta"
      @toggle="sidebarAbierta = !sidebarAbierta"
    />

    <!-- Overlay para cerrar la sidebar al tocar fuera -->
    <div
      v-if="sidebarAbierta"
      class="overlay"
      @click="sidebarAbierta = false"
    ></div>

    <main :class="['main-content', { 'shifted': sidebarAbierta && auth.isAuthenticated }]">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const sidebarAbierta = ref(false)
</script>

<style>
/* Botón Hamburguesa */
.menu-toggle {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 999;
  background: #1a237e;
  border: none;
  padding: 10px;
  border-radius: 5px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bar {
  width: 25px;
  height: 3px;
  background-color: white;
  border-radius: 2px;
}

.overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0,0,0,0.5);
  z-index: 998;
}

.main-content {
  width: 100%;
  min-height: 100vh;
  transition: padding-left 0.3s ease;
}

/* Opcional: empujar el contenido si quieres que no se tape */
/* .main-content.shifted { padding-left: 260px; } */

body { margin: 0; font-family: sans-serif; }
</style>
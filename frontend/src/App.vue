<template>
  <div class="app-layout">
    <Sidebar v-if="auth.isAuthenticated" @toggle="handleSidebarToggle" />

    <main :class="['main-content', { 'full-width': !isSidebarOpen || !auth.isAuthenticated }]">
      <div class="app-mobile-header">
        <BackButton variant="icon" />
        <div class="app-mobile-header-text">
          <div class="app-mobile-title">{{ headerTitle }}</div>
          <div v-if="headerSubtitle" class="app-mobile-subtitle">{{ headerSubtitle }}</div>
        </div>
        <div class="app-mobile-header-spacer"></div>
      </div>

      <div class="app-toolbar">
        <BackButton variant="pill" />
      </div>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import BackButton from './components/BackButton.vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const isSidebarOpen = ref(false)
const route = useRoute()

const headerTitle = computed(() => route.meta?.headerTitle || 'CLUB360')
const headerSubtitle = computed(() => route.meta?.headerSubtitle || '')

// Actualiza el estado local para expandir/contraer el contenido
const handleSidebarToggle = (state) => {
  isSidebarOpen.value = state
}
</script>

<style>
/* Estilos Globales */
html,
body,
#app {
  height: 100%;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
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

.app-toolbar {
  padding: 18px 20px 0;
}

.app-mobile-header {
  display: none;
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

  .app-toolbar {
    display: none;
  }

  .main-content {
    padding-top: 56px;
  }

  .app-mobile-header {
    position: sticky;
    top: 0;
    z-index: 1100;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 12px;
    background: #ffffff;
    border-bottom: 1px solid rgba(13, 18, 74, 0.08);
    box-shadow: 0 10px 24px rgba(17, 24, 39, 0.08);
  }

  .app-mobile-header-text {
    flex: 1;
    text-align: center;
    min-width: 0;
  }

  .app-mobile-title {
    font-weight: 900;
    color: #0d124a;
    font-size: 1rem;
    line-height: 1.1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .app-mobile-subtitle {
    margin-top: 2px;
    font-weight: 700;
    color: rgba(13, 18, 74, 0.6);
    font-size: 0.85rem;
    line-height: 1.1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .app-mobile-header-spacer {
    width: 40px;
  }
}
</style>
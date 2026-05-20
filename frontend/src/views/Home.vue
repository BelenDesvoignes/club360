<template>
  <div class="home-wrapper">
    
    <div v-if="!auth.isAuthenticated" class="welcome-hero">
      <div class="hero-content">
        <h1 class="main-logo">CLUB<span>360</span></h1>
        <div class="auth-buttons-vertical">
          <router-link to="/login" class="btn-full-orange">Iniciar sesión</router-link>
          <router-link to="/register" class="btn-full-white">Registrarse</router-link>
        </div>
      </div>
    </div>

    <div v-else>
      <AdminDashboard v-if="auth.user?.role === 'admin' || auth.role === 'admin'" />

      <DefaultDashboard v-else />
    </div>

  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
import AdminDashboard from '../components/AdminDashboard.vue'
import DefaultDashboard from '../components/DefaultDashboard.vue' 

const auth = useAuthStore()
</script>

<style scoped>
/* Contenedor Principal */
.home-wrapper {
  min-height: 100vh;
  background-color: #f8f9fa;
}

/* --- ESTILOS VISTA BIENVENIDA ORIGINALES --- */
.welcome-hero {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #2d658d;
  color: white;
  text-align: center;
}
.main-logo {
  font-size: 5rem;
  font-weight: 900;
  letter-spacing: 4px;
  margin-bottom: 50px;
}
.main-logo span {
  color: #ff6f00;
}
.auth-buttons-vertical {
  display: flex;
  flex-direction: column;
  gap: 15px;
  align-items: center;
}
.btn-full-orange {
  background: #ff6f00;
  color: white;
  width: 280px;
  padding: 16px;
  border-radius: 12px;
  text-decoration: none;
  font-weight: bold;
  font-size: 1.1rem;
  transition: transform 0.2s;
}
.btn-full-white {
  background: white;
  color: #0d124a;
  width: 280px;
  padding: 16px;
  border-radius: 12px;
  text-decoration: none;
  font-weight: bold;
  font-size: 1.1rem;
  transition: transform 0.2s;
}
.btn-full-orange:hover, .btn-full-white:hover {
  transform: scale(1.03);
}

@media (max-width: 600px) {
  .main-logo { font-size: 3.5rem; }
  .btn-full-orange, .btn-full-white { width: 240px; }
}
</style>
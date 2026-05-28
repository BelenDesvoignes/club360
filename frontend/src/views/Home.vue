<template>
  <div class="home-wrapper">

    <div v-if="!auth.isAuthenticated" class="welcome-hero">
      <div class="hero-content">
        <div class="logo-container">
          <img src="../assets/logo.png" alt="Club 360 Logo" class="logo-img" />
        </div>

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
  background-color: #ffffff; /* Aseguramos fondo blanco general */
}

/* --- ESTILOS VISTA BIENVENIDA --- */
.welcome-hero {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #ffffff;
  text-align: center;
}

/* Contenedor del logo centrado */
.logo-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  margin-bottom: 60px;
}

/* Logo significativamente más grande y nítido */
.logo-img {
  width: 420px; /* 👈 CAMBIÁ ESTO: Estaba en 280px, subilo a 420px para la compu */
  height: auto;
  object-fit: contain;
}

/* Botones de autenticación */
.auth-buttons-vertical {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}

.btn-full-orange {
  background: #2c303b;
  color: white;
  width: 280px;
  padding: 16px;
  border-radius: 12px;
  text-decoration: none;
  font-weight: bold;
  font-size: 1.1rem;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 12px rgba(255, 111, 0, 0.2);
}

.btn-full-white {
  background: #2d658d;
  color: #ffffff;
  width: 280px;
  padding: 16px;
  border-radius: 12px;
  border: 2px solid #2d658d;
  text-decoration: none;
  font-weight: bold;
  font-size: 1.1rem;
  transition: transform 0.2s, background-color 0.2s;
}

.btn-full-orange:hover, .btn-full-white:hover {
  transform: scale(1.03);
}

.btn-full-white:hover {
  background-color: #2d658d;
}

/* Ajustes para celulares */
@media (max-width: 600px) {
  .logo-img {
    width: 280px; /* 👈 AJUSTADO: Un tamaño imponente para celular sin romper la pantalla */
  }
  .btn-full-orange, .btn-full-white {
    width: 240px;
  }
}
</style>
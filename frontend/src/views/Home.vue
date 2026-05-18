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

    <div v-else class="dashboard">
      <header class="dashboard-banner">
        <div class="banner-text">
          <h1>¡Hola, {{ auth.userEmail.split('@')[0] }}!</h1>
        </div>
        <div class="user-avatar">
          {{ auth.userEmail[0].toUpperCase() }}
        </div>
      </header>

      <section class="content-section">
        <h2 class="section-title">Pensar que poner aca </h2>


      </section>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>

<style scoped>
/* Contenedor Principal */
.home-wrapper {
  min-height: 100vh;
  background-color: #f8f9fa;
}

/* --- ESTILOS VISTA BIENVENIDA (LA FOTO) --- */
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

/* --- ESTILOS DASHBOARD --- */
.dashboard-banner {
  background-color: #2d658d;
  padding: 60px 40px 100px 40px;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.banner-text h1 { margin: 0; font-size: 1.8rem; }
.banner-text p { margin: 5px 0 0; opacity: 0.8; font-size: 0.9rem; }

.user-avatar {
  width: 50px;
  height: 50px;
  background: #ff6f00;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1.2rem;
}

.content-section {
  max-width: 900px;
  margin: -60px auto 0;
  padding: 0 20px 40px;
}

.section-title {
  color: white;
  font-size: 1.1rem;
  margin-bottom: 20px;
  font-weight: 500;
}

.grid-acciones {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.card-item {
  background: white;
  padding: 20px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  cursor: pointer;
  transition: all 0.2s ease;
}

.card-item:hover {
  transform: scale(1.02);
  border-color: #ff6f00;
}

.icon-box {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  margin-right: 20px;
}

.bg-orange { background: #fff3e0; }
.bg-blue { background: #e3f2fd; }
.bg-green { background: #e8f5e9; }

.card-info h3 { margin: 0; font-size: 1.1rem; color: #333; }
.card-info p { margin: 2px 0 0; font-size: 0.85rem; color: #777; }

.arrow { color: #ccc; font-size: 1.2rem; margin-left: auto; }

.info-banner {
  margin-top: 30px;
  background: #fff;
  padding: 15px;
  border-radius: 12px;
  border-left: 5px solid #ff6f00;
  font-size: 0.9rem;
  color: #555;
}

@media (max-width: 600px) {
  .main-logo { font-size: 3.5rem; }
  .btn-full-orange, .btn-full-white { width: 240px; }
  .dashboard-banner { padding: 40px 20px 80px 20px; }
}
</style>
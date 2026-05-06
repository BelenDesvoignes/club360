<template>
  <div class="home-wrapper">
    <div v-if="!auth.isAuthenticated" class="welcome-hero">
      <div class="hero-content">
        <h1>CLUB<span>360</span></h1>
        <p>Tu centro deportivo en un solo lugar.</p>
        <div class="auth-buttons">
          <router-link to="/login" class="btn-primary">Iniciar Sesión</router-link>
          <router-link to="/register" class="btn-secondary">Registrarse</router-link>
        </div>
      </div>
    </div>

    <div v-else class="dashboard">
      <header class="dashboard-banner">
        <div class="banner-text">
          <h1>¡Hola, {{ auth.userEmail.split('@')[0] }}!</h1>
          <p>Panel de Control • CLUB360</p>
        </div>
        <div class="user-avatar">
          {{ auth.userEmail[0].toUpperCase() }}
        </div>
      </header>

      <section class="content-section">
        <h2 class="section-title">Acciones principales</h2>
        <div class="grid-acciones">
          <div class="card-item" @click="$router.push('/turnos')">
            <div class="icon-box bg-orange">📅</div>
            <div class="card-info">
              <h3>Turnos</h3>
              <p>Reserva tu lugar ahora</p>
            </div>
            <span class="arrow">→</span>
          </div>

          <div class="card-item" @click="$router.push('/reservas')">
            <div class="icon-box bg-blue">📝</div>
            <div class="card-info">
              <h3>Mis Reservas</h3>
              <p>Gestiona tus clases</p>
            </div>
            <span class="arrow">→</span>
          </div>

          <div class="card-item" @click="$router.push('/abonos')">
            <div class="icon-box bg-green">💳</div>
            <div class="card-info">
              <h3>Mi Abono</h3>
              <p>Estado de cuenta</p>
            </div>
            <span class="arrow">→</span>
          </div>
        </div>

        <div class="info-banner">
          <p><strong>💡 Tip:</strong> Recuerda cancelar tus reservas con al menos 48 horas de anticipación.</p>
        </div>
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

/* Banner Superior (Azul Oscuro como la imagen) */
.dashboard-banner {
  background-color: #0d124a;
  padding: 60px 40px 100px 40px; /* Mucho padding abajo para el efecto de solapamiento */
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
  box-shadow: 0 4px 10px rgba(0,0,0,0.2);
}

/* Sección de Contenido (Sube un poco para pisar el azul) */
.content-section {
  max-width: 900px;
  margin: -60px auto 0; /* Margen negativo para el efecto visual */
  padding: 0 20px 40px;
}

.section-title {
  color: white; /* Se ve sobre el azul */
  font-size: 1.1rem;
  margin-bottom: 20px;
  font-weight: 500;
}

/* Grid de Tarjetas (Estilo Lista de la imagen) */
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
  border: 1px solid transparent;
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

.card-info { flex-grow: 1; }
.card-info h3 { margin: 0; font-size: 1.1rem; color: #333; }
.card-info p { margin: 2px 0 0; font-size: 0.85rem; color: #777; }

.arrow { color: #ccc; font-size: 1.2rem; }

/* Banner de Tips */
.info-banner {
  margin-top: 30px;
  background: #fff;
  padding: 15px;
  border-radius: 12px;
  border-left: 5px solid #ff6f00;
  font-size: 0.9rem;
  color: #555;
}

/* Hero para no logueados */
.welcome-hero {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #0d124a;
  color: white;
  text-align: center;
}
.hero-content h1 span { color: #ff6f00; }
.auth-buttons { margin-top: 30px; display: flex; gap: 10px; justify-content: center; }
.btn-primary { background: #ff6f00; color: white; padding: 12px 25px; border-radius: 10px; text-decoration: none; font-weight: bold; }
.btn-secondary { border: 2px solid white; color: white; padding: 10px 25px; border-radius: 10px; text-decoration: none; }

/* Responsive */
@media (max-width: 600px) {
  .dashboard-banner { padding: 40px 20px 80px 20px; }
  .banner-text h1 { font-size: 1.4rem; }
}
</style>
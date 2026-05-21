<template>
  <div class="dashboard">
    <header class="dashboard-banner">
      <div class="banner-text">
        <h1>¡Hola, {{ auth.userEmail ? auth.userEmail.split('@')[0] : 'Usuario' }}!</h1>
      </div>
      <div class="user-avatar" v-if="auth.userEmail">
        {{ auth.userEmail[0].toUpperCase() }}
      </div>
    </header>

    <section class="content-section">
      <h2 class="section-title">Pensar que poner aca </h2>
    </section>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>

<style scoped>
.dashboard-banner {
  background-color: #2d658d;
  padding: 60px 40px 100px 40px;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.banner-text h1 { margin: 0; font-size: 1.8rem; }
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
  color: white;
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
</style>
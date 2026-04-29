<template>
  <div class="container">
    <div class="card">
      <h1>Iniciar Sesión 🔐</h1>
      <p class="subtitle">Próximamente...</p>
      <p class="back"><router-link to="/">← Volver</router-link></p>
    </div>
  </div>
</template>

<style scoped>
.container { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f4f7f6; font-family: 'Segoe UI', sans-serif; }
.card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center; }
.back { margin-top: 1rem; }
.back a { color: #1a237e; text-decoration: none; }
</style>
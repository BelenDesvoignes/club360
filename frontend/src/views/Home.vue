<template>
  <div class="home">
    <div class="content">
      <div class="logo-section">
        <h1 class="club-name">CLUB<span>360</span></h1>
        <p class="tagline">    </p>
      </div>

      <div class="buttons">
        <router-link to="/login" class="btn btn-primary">Iniciar Sesión</router-link>
        <router-link to="/register" class="btn btn-secondary">Registrarse</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  min-height: 100vh;
  background: linear-gradient(160deg, #1a237e 60%, #ff6f00 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  font-family: 'Segoe UI', sans-serif;
}

.content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3rem;
  padding: 2rem;
}

.logo-section {
  text-align: center;
}

.club-name {
  font-size: 4rem;
  font-weight: 900;
  color: white;
  letter-spacing: 4px;
  margin: 0;
  text-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.club-name span {
  color: #ff6f00;
}

.tagline {
  color: rgba(255,255,255,0.8);
  font-size: 1.1rem;
  margin-top: 0.5rem;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.buttons {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
  max-width: 300px;
}

.btn {
  display: block;
  padding: 1rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 700;
  text-align: center;
  text-decoration: none;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.2);
}

.btn-primary {
  background: #ff6f00;
  color: white;
}

.btn-secondary {
  background: white;
  color: #1a237e;
}

@media (max-width: 480px) {
  .club-name { font-size: 3rem; }
}
</style>
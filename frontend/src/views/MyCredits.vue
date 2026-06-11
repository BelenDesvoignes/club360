<template>
  <div class="page">
    <div class="container">
      
      <header class="header">
        <h1>Mis créditos</h1>
        <p class="subtitle">
          Listado de tus créditos a favor por deporte. Usalos antes de su fecha de vencimiento.
        </p>
      </header>

      <section class="credits-section" aria-label="Créditos disponibles">
        
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>Cargando tus créditos...</p>
        </div>

        <div v-else>
          <div v-if="sortedCredits.length === 0" class="empty-state">
            No tenés créditos disponibles en este momento. 
          </div>

          <div v-else class="credits-list">
            <div 
              v-for="credit in sortedCredits" 
              :key="credit.id" 
              class="credit-row"
            >
              <div class="sport-container">
                <span class="sport-name">{{ getSportName(credit.activity_id) }}</span>
              </div>

              <div class="expiry-container">
                <span class="calendar-icon">📅</span>
                <div class="expiry-info">
                  <span class="expiry-label">Vence el:</span>
                  <span class="expiry-date">{{ formatDate(credit.expiry_date) }}</span>
                </div>
              </div>

              <div class="action-container">
                <button 
                  @click="handleReserveWithCredit(credit)" 
                  class="primary"
                >
                  Solicitar clase con crédito
                </button>
              </div>
            </div>
          </div>
        </div>

      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const loading = ref(true)
const rawCredits = ref([])


const sortedCredits = computed(() => {
  return [...rawCredits.value].sort((a, b) => {
    if (!a.expiry_date) return 1
    if (!b.expiry_date) return -1
    return new Date(a.expiry_date) - new Date(b.expiry_date)
  })
})

const fetchMyCredits = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('/credits/me', {
      headers: { 
        Authorization: `Bearer ${token}` 
      }
    })
    rawCredits.value = res.data || []
  } catch (error) {
    console.error("Error al obtener los créditos del backend:", error)
  } finally {
    loading.value = false
  }
}

const getSportName = (activityId) => {
  const sports = {
    1: 'Fútbol',
    2: 'Pádel',
    3: 'Vóley',
    4: 'Básquet'
  }
  return sports[activityId] || 'Deporte General'
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Fin de mes'
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}


const handleReserveWithCredit = (credit) => {
  const deporte = getSportName(credit.activity_id)
  alert(`Abriendo flujo de reserva para ${deporte}.\nCrédito ID seleccionado: ${credit.id}`);
  // Acá podés meter un router.push() o emitir el evento según tu flujo de reservas
}

onMounted(() => {
  fetchMyCredits()
})
</script>

<style scoped>
.page {
  width: 100%;
  padding: 28px 40px 40px;
  max-width: 1200px;
  margin: 0 auto;
  min-height: 100vh;
  background: transparent;
}

.container {
  max-width: none;
  margin: 0;
}

.header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 18px;
}

.header h1 {
  font-size: 2.5rem;
  color: #2d658d;
  font-weight: 900;
  margin: 0 0 10px;
}

.subtitle {
  margin: 0;
  color: #5a8849;
  font-weight: 400;
  font-size: 1.1rem;
}

.section-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 22px 0 10px;
}

.section-title h2 {
  margin: 0;
  font-size: 1rem;
  color: #0d124a;
  font-weight: 700;
}

/* Sección blanca contenedora */
.credits-section {
  background: white;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

/* Estado vacío estilo dashed */
.empty-state {
  padding: 14px;
  border-radius: 12px;
  border: 1px dashed rgba(45, 101, 141, 0.35);
  color: #2d658d;
  background: rgba(45, 101, 141, 0.06);
  font-size: 1rem;
}

/* Estructura del listado lineal */
.credits-list {
  display: flex;
  flex-direction: column;
}

.credit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 8px;
  border-bottom: 1px solid rgba(13, 18, 74, 0.08);
  gap: 20px;
}

.credit-row:last-child {
  border-bottom: none;
}

/* Bloque del Deporte minimalista */
.sport-container {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 180px;
}

.sport-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: #0d124a; /* Azul corporativo */
}

/* Bloque de Vencimiento */
.expiry-container {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 160px;
}

.calendar-icon {
  font-size: 1.1rem;
  opacity: 0.5;
}

.expiry-info {
  display: flex;
  flex-direction: column;
}

.expiry-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  font-weight: 700;
  color: #9ca3af;
  letter-spacing: 0.5px;
}

.expiry-date {
  font-size: 0.95rem;
  font-weight: 700;
  color: #b43b3b; /* Rojo sutil de vencimiento */
}

/* Botón Verde idéntico a addcard.vue */
.primary {
  border: none;
  border-radius: 12px;
  padding: 12px 20px;
  font-size: 1rem;
  font-weight: 800;
  color: white;
  background: #5a8849;
  cursor: pointer;
  transition: transform 0.12s ease, filter 0.12s ease;
  white-space: nowrap;
}

.primary:hover {
  filter: brightness(0.98);
}

.primary:active {
  transform: translateY(1px);
}

/* Estado de carga */
.loading-state {
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #0d124a;
  font-weight: 700;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid rgba(45, 101, 141, 0.15);
  border-radius: 50%;
  border-top-color: #2d658d;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Adaptabilidad mobile */
@media (max-width: 768px) {
  .credit-row {
    flex-direction: column;
    align-items: flex-start;
    padding: 16px 4px;
    gap: 14px;
  }
  .sport-container, 
  .expiry-container,
  .action-container {
    width: 100%;
  }
  .primary {
    width: 100%;
    text-align: center;
  }
}
</style>
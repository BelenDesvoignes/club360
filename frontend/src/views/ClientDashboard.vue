<template>
  <div class="dashboard-layout">
    <header class="club-banner">
      <img alt="Fachada Club 360" class="banner-bg-img" :src="'/sports/entrance.png'" />
      <div class="banner-overlay"></div>
      <div class="banner-content">
        <p class="banner-subtitle">Bienvenido de nuevo</p>
        <h1>{{ nombreCompleto }}</h1>
      </div>
    </header>

    <div class="cards-grid">

      <!-- Abono activo -->
      <div class="card" v-for="ab in abonos" :key="ab.subscription_id">
        <div class="card-label">
          <i class="ti ti-credit-card" aria-hidden="true"></i>
           ABONO ACTIVO
       </div>
        <p class="card-value">{{ ab.actividad }}</p>
        <div class="progress-bar-wrap">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: calcPorcentaje(ab.valid_to) + '%' }" :class="{ 'fill-red': calcDias(ab.valid_to) <= 3 }"></div>
          </div>
          <span class="progress-label" :class="{ 'text-red': calcDias(ab.valid_to) <= 3 }">{{ calcDias(ab.valid_to) }} días</span>
        </div>
        <p class="card-sub">Vence el {{ formatFecha(ab.valid_to) }}</p>
      </div>

      <!-- Próxima clase -->
      <div class="card">
        <div class="card-label">
          <i class="ti ti-calendar-event" aria-hidden="true"></i>
          PRÓXIMA CLASE
        </div>
        <template v-if="loading">
          <div class="skeleton skeleton-text" style="width:55%; height:1.4rem; margin-bottom:8px;"></div>
          <div class="skeleton skeleton-text" style="width:35%; height:0.9rem;"></div>
        </template>
        <template v-else-if="proximaClase">
          <p class="card-value">{{ proximaClase.activity_name }}</p>
          <p class="card-sub">{{ labelFechaClase }} • {{ proximaClase.start_time }} hs</p>
          <div class="badge-green">
            <i class="ti ti-clock" aria-hidden="true"></i>
            {{ tiempoHastaClase }}
          </div>
        </template>
        <template v-else>
          <p class="card-value no-data">Sin clases reservadas</p>
          <router-link to="/reservas" class="link-action">Reservar turno →</router-link>
        </template>
      </div>

      <!-- Clases este mes -->
      <div class="card">
        <div class="card-label">
          <i class="ti ti-chart-bar" aria-hidden="true"></i>
          CLASES ESTE MES
        </div>
        <template v-if="loading">
          <div class="skeleton skeleton-text" style="width:40%; height:2.2rem;"></div>
        </template>
        <template v-else>
          <p class="card-big-number">{{ asistenciasMes }}</p>
          <div class="mini-bar-chart">
            <div v-for="(val, i) in barrasAsistencia" :key="i" class="bar" :class="{ 'bar-active': i >= barrasAsistencia.length - 2 }" :style="{ height: val + '%' }"></div>
          </div>
        </template>
      </div>
    </div>

    <!-- Tip del día -->
    <div class="tip-card">
      <div class="tip-icon">
        <i class="ti ti-bulb" aria-hidden="true"></i>
      </div>
      <div class="tip-body">
        <p class="card-label" style="margin-bottom:4px;">TIP DEL DÍA</p>
        <p class="tip-text">{{ tipActual }}</p>
      </div>
      <button class="tip-btn" @click="nextTip" aria-label="Siguiente tip">
        <i class="ti ti-refresh"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const loading = ref(true)

const abonos = ref([])
const proximaClase = ref(null)
const asistenciasMes = ref(0)

// Helpers para los abonos
const calcDias = (validTo) => {
  const diff = Math.ceil((new Date(validTo) - new Date()) / (1000 * 60 * 60 * 24))
  return Math.max(0, diff)
}
const calcPorcentaje = (validTo) => Math.min(100, Math.round((calcDias(validTo) / 30) * 100))
const formatFecha = (validTo) => new Date(validTo).toLocaleDateString('es-AR', { day: 'numeric', month: 'long' })

const tips = [
  'Recordá traer tu botella de agua y recargarla en los dispenser del club.',
  'Llegá 10 minutos antes para entrar al calor previo con el profesor.',
  'Usá calzado adecuado para la cancha y protegé tus rodillas.',
  'Después de entrenar, estirá al menos 5 minutos para evitar lesiones.',
  'Mantené activo tu abono pagando entre el 1 y el 10 de cada mes.',
  'Si no podés venir, cancelá tu reserva con 48 hs de anticipación para no perder el crédito.',
]
const tipIndex = ref(0)
const tipActual = computed(() => tips[tipIndex.value])
const nextTip = () => { tipIndex.value = (tipIndex.value + 1) % tips.length }

const nombreCompleto = computed(() => {
  if (!auth.user) return ''
  return auth.user.first_name
})

const labelFechaClase = computed(() => {
  if (!proximaClase.value?.date) return ''
  const hoy = new Date().toISOString().split('T')[0]
  const manana = new Date(Date.now() + 86400000).toISOString().split('T')[0]
  if (proximaClase.value.date === hoy) return 'Hoy'
  if (proximaClase.value.date === manana) return 'Mañana'
  return new Date(proximaClase.value.date).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })
})

const tiempoHastaClase = computed(() => {
  if (!proximaClase.value) return ''
  const ahora = new Date()
  const [h, m] = proximaClase.value.start_time.split(':').map(Number)
  const claseDate = new Date(proximaClase.value.date)
  claseDate.setHours(h, m, 0, 0)
  const diffMin = Math.round((claseDate - ahora) / 60000)
  if (diffMin < 0) return 'En curso'
  if (diffMin < 60) return `En ${diffMin} min`
  const horas = Math.floor(diffMin / 60)
  return `En ${horas} hora${horas > 1 ? 's' : ''}`
})

const barrasAsistencia = computed(() => {
  const total = asistenciasMes.value || 1
  return [40, 55, 45, 70, Math.min(100, Math.round((total / 12) * 90)), 60]
})

onMounted(async () => {
  loading.value = true
  try {
    const [resAbonos, resProxima, resAsistencias] = await Promise.all([
      axios.get('/subscriptions/my-active-all'),
      axios.get('/bookings/my-next'),
      axios.get('/attendances/my-month-count'),
    ])
    abonos.value = resAbonos.data
    proximaClase.value = resProxima.data
    asistenciasMes.value = resAsistencias.data.count ?? 0
  } catch (e) {
    console.error('Error cargando dashboard del cliente:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dashboard-layout {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  font-family: system-ui, -apple-system, sans-serif;
}

.club-banner {
  position: relative;
  height: 220px;
  border-radius: 20px;
  overflow: hidden;
}
.banner-bg-img { width: 100%; height: 100%; object-fit: cover; object-position: center 40%; }
.banner-overlay { position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.15) 100%); }
.banner-content { position: absolute; bottom: 24px; left: 28px; color: white; z-index: 2; }
.banner-subtitle { margin: 0 0 2px; font-size: 13px; opacity: 0.8; }
.banner-content h1 { margin: 0; font-size: 2rem; font-weight: 500; text-shadow: 0 2px 8px rgba(0,0,0,0.5); }

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.card {
  background: white;
  border: 1px solid #e1e6eb;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 130px;
}

.card-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #718096;
  letter-spacing: 0.4px;
  margin-bottom: 4px;
}
.card-label i { font-size: 15px; }

.card-value { margin: 0; font-size: 1.3rem; font-weight: 500; color: #1a202c; }
.card-sub { margin: 0; font-size: 12px; color: #718096; }
.card-big-number { margin: 0; font-size: 2.4rem; font-weight: 500; color: #1a202c; line-height: 1; }
.no-data { font-size: 1rem !important; color: #a0aec0 !important; }

.link-action {
  font-size: 12px;
  color: #2d658d;
  text-decoration: none;
  font-weight: 600;
  margin-top: 4px;
}

.progress-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.progress-bar {
  flex: 1;
  height: 4px;
  background: #edf2f7;
  border-radius: 2px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: #48bb78;
  border-radius: 2px;
  transition: width 0.4s ease;
}
.fill-red { background: #e53e3e !important; }
.progress-label { font-size: 12px; color: #48bb78; font-weight: 600; white-space: nowrap; }
.text-red { color: #e53e3e !important; }

.badge-green {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #e8f5e9;
  color: #2e7d32;
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 20px;
  margin-top: 6px;
  width: fit-content;
}
.badge-green i { font-size: 13px; }

.mini-bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 5px;
  height: 28px;
  margin-top: 10px;
}
.bar { flex: 1; background: #edf2f7; border-radius: 2px; }
.bar-active { background: #2d658d; }

.tip-card {
  background: white;
  border: 1px solid #e1e6eb;
  border-radius: 16px;
  padding: 18px 20px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.tip-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff3e0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.tip-icon i { font-size: 18px; color: #ff6f00; }
.tip-body { flex: 1; }
.tip-text { margin: 0; font-size: 14px; color: #2d3748; line-height: 1.5; }
.tip-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: #718096;
}
.tip-btn i { font-size: 18px; }

.skeleton {
  background: linear-gradient(90deg, #f0f2f5 25%, #e6e8ec 50%, #f0f2f5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite ease-in-out;
  border-radius: 4px;
  display: inline-block;
}
.skeleton-text { height: 1em; margin-bottom: 4px; }
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 600px) {
  .dashboard-layout { padding: 16px; }
  .club-banner { height: 170px; }
  .cards-grid { grid-template-columns: 1fr; }
}
</style>
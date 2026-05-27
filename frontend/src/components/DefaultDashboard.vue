<template>
  <div class="dashboard-layout">
    <header class="club-banner">
      <img alt="Fachada Club 360" class="banner-bg-img" :src="'/sports/entrance.png'" />
      <div class="banner-overlay"></div>
      <div class="banner-content">
        <p class="banner-subtitle">Cuenta de empleado</p>
        <h1 class="user-name">{{ nombreCompleto }}</h1>
      </div>
    </header>

    <div class="dashboard-grid">
      <div class="main-column">
        <section class="metrics-row">
          
          <div class="metric-card">
            <div class="card-label">
              <i class="ti ti-calendar-event" aria-hidden="true"></i>
              RESERVAS DE HOY
            </div>
            <div class="metric-body">
              <div v-if="loading" class="skeleton skeleton-text" style="width: 50px; height: 2.2rem;"></div>
              <template v-else>
                <span class="card-big-number">{{ reservasHoy }}</span>
                <span class="text-green-change">Activas</span>
              </template>
            </div>
            <div class="mini-bar-chart">
              <div class="bar" style="height: 40%"></div>
              <div class="bar" style="height: 55%"></div>
              <div class="bar" style="height: 45%"></div>
              <div class="bar" style="height: 70%"></div>
              <div class="bar" style="height: 90%"></div>
              <div class="bar" style="height: 65%"></div>
            </div>
          </div>

          <div class="metric-card jc-center">
            <div class="card-label">
              <i class="ti ti-credit-card" aria-hidden="true"></i>
              ABONOS ACTIVOS
            </div>
            <div class="metric-body">
              <div v-if="loading" class="skeleton skeleton-text" style="width: 60px; height: 2.2rem;"></div>
              <span v-else class="card-big-number text-green">{{ totalAbonosActivos }}</span>
            </div>
          </div>

          <div class="metric-card jc-center">
            <div class="card-label">
              <i class="ti ti-user-x" aria-hidden="true"></i>
              CLIENTES SUSPENDIDOS
            </div>
            <div class="metric-body">
              <div v-if="loading" class="skeleton skeleton-text" style="width: 50px; height: 2.2rem;"></div>
              <span v-else class="card-big-number text-red">{{ totalSuspensiones }}</span>
            </div>
          </div>
        </section>

        <section class="classes-section">
          <div class="section-header">
            <h3 class="section-title-grid">PRÓXIMAS ACTIVIDADES DEL DÍA</h3>
            <router-link to="/clases" class="view-all-link">Ver Agenda Completa →</router-link>
          </div>
          
          <div class="classes-flex-container">
            <template v-if="loading">
              <div v-for="i in 2" :key="'sk-clase-' + i" class="class-card">
                <div class="class-info-main">
                  <div class="skeleton skeleton-text" style="width: 70%; height: 1.4rem; margin-bottom: 6px;"></div>
                  <div class="skeleton skeleton-text" style="width: 50%; height: 0.85rem;"></div>
                </div>
                <div class="class-meta">
                  <div class="skeleton" style="width: 50px; height: 12px;"></div>
                </div>
              </div>
            </template>

            <template v-else>
              <div v-for="clase in proximasClasesFiltradas" :key="clase.id" class="class-card" :class="{ 'border-red': clase.booked_count >= (clase.capacity || clase.max_capacity) }">
                <div class="class-info-main">
                  <p class="card-value-title">{{ clase.activity_name }}</p>
                  <p class="class-details-sub">
                    {{ clase.template.start_time }} hs 
                  </p>
                </div>
                
                <div class="class-meta">
                  <div class="spots-status">
                    <span v-if="clase.booked_count >= (clase.capacity || clase.max_capacity)" class="text-red font-bold" style="font-size: 11px;">COMPLETO</span>
                    <span v-else class="spots-text">{{ clase.booked_count }} / {{ clase.capacity || clase.max_capacity }} cupos</span>
                    <div class="progress-bar-wrap">
                      <div class="progress-bar">
                        <div class="progress-fill" :class="{ 'bg-red': clase.booked_count >= (clase.capacity || clase.max_capacity), 'bg-green': (clase.booked_count / (clase.capacity || clase.max_capacity)) < 0.8 }" :style="{ width: (clase.booked_count / (clase.capacity || clase.max_capacity)) * 100 + '%' }"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div v-if="proximasClasesFiltradas.length === 0" class="no-data-placeholder">
                No hay más clases programadas para el resto del día.
              </div>
            </template>
          </div>
        </section>
      </div>

      <aside class="activity-column">
        <div class="activity-card-container">
          <div class="activity-header">
            <span class="live-dot"></span>
            <h3 class="section-title-grid" style="margin: 0;">HISTORIAL DE ACTIVIDAD</h3>
          </div>
          <div class="activity-timeline-minimal">
            <template v-if="loading">
              <div v-for="i in 3" :key="'sk-act-' + i" class="timeline-node-item">
                <div class="dot" style="background: #e2e8f0;"></div>
                <div class="node-content" style="width: 100%;">
                  <div class="skeleton skeleton-text" style="width: 90%; height: 0.8rem; margin-bottom: 4px;"></div>
                  <div class="skeleton skeleton-text" style="width: 30%; height: 0.7rem;"></div>
                </div>
              </div>
            </template>

            <template v-else>
              <div v-for="(actividad, index) in historialActividad" :key="index" class="timeline-node-item">
                <div class="dot orange-dot"></div>
                <div class="node-content">
                  <p v-html="actividad.texto"></p>
                  <span class="node-time">{{ actividad.tiempo }}</span>
                </div>
              </div>
            </template>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { useAppClockStore } from '../stores/appClock'

const loading = ref(true)
const auth = useAuthStore()
const clock = useAppClockStore()

// Estados reactivos
const reservasHoy = ref(0)
const totalAbonosActivos = ref(0)
const totalSuspensiones = ref(0)
const historialActividad = ref([])
const todasLasClasesDelDia = ref([])
const proximasClasesFiltradas = ref([])
let intervaloActualizacion = null

// CAPTURA REAL DEL USUARIO LOGUEADO
const nombreCompleto = computed(() => {
  if (!auth.user) return 'Personal Club360'
  return `${auth.user.first_name} ${auth.user.last_name || ''}`.trim()
})

// LOGICA FILTRO: SIN REPETIDOS Y OCULTADO AL COMENZAR
const procesarFiltroClases = () => {
  reservasHoy.value = todasLasClasesDelDia.value.reduce((acumulador, clase) => {
    return acumulador + (clase.booked_count || 0)
  }, 0)

  const ahora = new Date()
  const horaActualStr = ahora.toTimeString().slice(0, 5)

  const clasesFuturas = todasLasClasesDelDia.value.filter(clase => {
    return clase.template.start_time >= horaActualStr
  })

  const mapeoActividades = {}
  clasesFuturas.forEach(clase => {
    const nombreActividad = clase.activity_name
    if (!mapeoActividades[nombreActividad]) {
      mapeoActividades[nombreActividad] = clase
    } else {
      if (clase.template.start_time < mapeoActividades[nombreActividad].template.start_time) {
        mapeoActividades[nombreActividad] = clase
      }
    }
  })

  proximasClasesFiltradas.value = Object.values(mapeoActividades)
    .sort((a, b) => a.template.start_time.localeCompare(b.template.start_time))
    .slice(0, 4)
}

const inicializarDashboard = async () => {
  loading.value = true
  try {
    const [resSummary, resShifts] = await Promise.all([
      axios.get('/dashboard/summary'),
      axios.get('/shifts/instances')
    ])

    totalAbonosActivos.value = resSummary.data.active_subscriptions
    totalSuspensiones.value = resSummary.data.suspended_clients
    historialActividad.value = resSummary.data.activity_feed

    const hoyStr = clock.effectiveTodayStr
    todasLasClasesDelDia.value = resShifts.data.filter(clase => clase.date === hoyStr)
    
    procesarFiltroClases()
  } catch (error) {
    console.error("Error cargando el dashboard:", error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  inicializarDashboard()
  intervaloActualizacion = setInterval(() => {
    procesarFiltroClases()
  }, 60000)
})

onUnmounted(() => {
  if (intervaloActualizacion) clearInterval(intervaloActualizacion)
})
</script>

<style scoped>
.dashboard-layout {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  font-family: system-ui, -apple-system, sans-serif;
}

/* BANNER COMPACTO */
.club-banner {
  position: relative;
  height: 180px;
  border-radius: 20px;
  overflow: hidden;
}
.banner-bg-img { width: 100%; height: 100%; object-fit: cover; object-position: center 40%; }
.banner-overlay { position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.2) 100%); }
.banner-content { position: absolute; bottom: 20px; left: 24px; color: white; z-index: 2; }
.banner-subtitle { margin: 0 0 2px; font-size: 12px; opacity: 0.85; letter-spacing: 0.5px; text-transform: uppercase; }
.user-name { margin: 0; font-size: 1.8rem; font-weight: 600; text-shadow: 0 2px 6px rgba(0,0,0,0.4); text-transform: capitalize; }

/* GRID PRINCIPAL */
.dashboard-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
.main-column { display: flex; flex-direction: column; gap: 20px; }
.metrics-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }

/* ESTILOS DE TARJETAS MINIATURA */
.metric-card {
  background: white;
  border: 1px solid #e1e6eb;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 110px;
}
.jc-center { justify-content: center !important; gap: 4px; }

.card-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10.5px;
  font-weight: 700;
  color: #718096;
  letter-spacing: 0.5px;
}
.card-label i { font-size: 13px; }

.metric-body { display: flex; align-items: baseline; gap: 8px; margin-top: 6px; }
.card-big-number { margin: 0; font-size: 2.2rem; font-weight: 600; color: #1a202c; line-height: 1; }

.text-green { color: #48bb78 !important; }
.text-red { color: #e53e3e !important; }
.text-green-change { color: #48bb78; font-size: 0.8rem; font-weight: 600; }

.mini-bar-chart { display: flex; align-items: flex-end; gap: 4px; height: 20px; margin-top: 4px; }
.mini-bar-chart .bar { flex: 1; background: #edf2f7; border-radius: 1px; }

/* SECCIÓN CONTENEDORES DE CONTENIDO */
.classes-section, .activity-card-container {
  background: white;
  border: 1px solid #e1e6eb;
  border-radius: 14px;
  padding: 18px;
}

.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.section-title-grid { font-size: 11.5px; font-weight: 700; color: #4a5568; letter-spacing: 0.8px; margin-bottom: 12px; text-transform: uppercase; }
.view-all-link { color: #2d658d; font-size: 0.8rem; text-decoration: none; font-weight: 600; }
.view-all-link:hover { text-decoration: underline; }

/* CONTENEDOR FLEXIBLE DE CLASES */
.classes-flex-container { 
  display: flex; 
  flex-wrap: wrap; 
  gap: 16px; 
  justify-content: flex-start;
}

.class-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 14px;
  flex: 1 1 240px;
  max-width: 280px; 
}

/* CAJA CONTENEDORA DE TEXTOS CON ALINEACIÓN PERFECTA */
.class-info-main {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  width: 100%;
}

.card-value-title { 
  margin: 0; 
  font-size: 1.3rem; 
  font-weight: 700; 
  color: #1a202c; 
  letter-spacing: -0.3px;
  text-align: left;
}

.class-details-sub { 
  margin: 4px 0 0; 
  font-size: 0.82rem; 
  color: #718096; 
  font-weight: 500;
  text-align: left;
  line-height: 1.2;
}

.class-meta { display: flex; justify-content: space-between; align-items: center; margin-top: 2px; }
.spots-status { width: 100%; }
.spots-text { font-size: 0.78rem; color: #4a5568; display: block; margin-bottom: 4px; font-weight: 600; }

.progress-bar-wrap { display: flex; align-items: center; width: 100%; }
.progress-bar { flex: 1; height: 5px; background: #edf2f7; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; transition: width 0.4s ease; }

.no-data-placeholder { width: 100%; padding: 20px; text-align: center; color: #718096; font-size: 0.85rem; }

/* HISTORIAL COMPACTO */
.activity-column { grid-column: 2; }
.activity-header { display: flex; align-items: center; gap: 6px; margin-bottom: 16px; }
.live-dot { width: 6px; height: 6px; background: #48bb78; border-radius: 50%; }
.activity-timeline-minimal { display: flex; flex-direction: column; gap: 16px; position: relative; padding-left: 4px; }
.activity-timeline-minimal::before { content: ''; position: absolute; left: 8px; top: 6px; bottom: 6px; width: 2px; background: #edf2f7; }
.timeline-node-item { display: flex; gap: 12px; align-items: flex-start; position: relative; }
.dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 4px; z-index: 1; box-shadow: 0 0 0 3px white; }
.orange-dot { background-color: #ff6f00; }
.node-content p { margin: 0; font-size: 0.82rem; color: #2d3748; line-height: 1.3; }
.node-time { font-size: 0.75rem; color: #9ab0c5; display: block; margin-top: 1px; }

.font-bold { font-weight: 700; }
.border-red { border-color: #fecaca; }
.bg-red { background-color: #e53e3e !important; }
.bg-green { background-color: #48bb78 !important; }

/* SKELETON ANIMADO */
.skeleton {
  background: linear-gradient(90deg, #f0f2f5 25%, #e6e8ec 50%, #f0f2f5 75%);
  background-size: 200% 100%;
  animation: loading-shimmer 1.4s infinite ease-in-out;
  border-radius: 4px;
  display: inline-block;
}
.skeleton-text { height: 1em; margin-bottom: 4px; }
@keyframes loading-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* RESPONSIVE */
@media (max-width: 900px) {
  .dashboard-grid { grid-template-columns: 1fr; gap: 16px; }
  .activity-column { grid-column: 1; }
  .metrics-row { grid-template-columns: 1fr; gap: 10px; }
  .classes-flex-container { justify-content: center; }
  .class-card { max-width: 100%; }
  .club-banner { height: 140px; }
  .user-name { font-size: 1.5rem; }
}
</style>
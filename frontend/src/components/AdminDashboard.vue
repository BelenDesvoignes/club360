<template>
  <div class="dashboard-layout">
    <header class="club-banner">
      <img alt="Fachada Club 360" class="banner-bg-img" :src="'/sports/entrance.png'" />
      <div class="banner-overlay"></div>
      <div class="banner-content">
        <h1>Bienvenido de nuevo, Admin</h1>
      </div>
    </header>

    <div class="dashboard-grid">
      <div class="main-column">
        <!-- SECCIÓN METRICAS -->
        <section class="metrics-row animate-fade-in">
          
          <!-- Reservas de Hoy -->
          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-title">RESERVAS DE HOY</span>
            </div>
            <div class="metric-body">
              <div v-if="loading" class="skeleton skeleton-text" style="width: 60px; height: 2.4rem;"></div>
              <template v-else>
                <span class="metric-value">{{ reservasHoy }}</span>
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

          <!-- Abonos Activos -->
          <div class="metric-card jc-center">
            <div class="metric-header">
              <span class="metric-title">ABONOS ACTIVOS</span>
            </div>
            <div class="metric-body">
              <div v-if="loading" class="skeleton skeleton-text" style="width: 80px; height: 2.4rem;"></div>
              <span v-else class="metric-value text-green">{{ totalAbonosActivos }}</span>
            </div>
          </div>

          <!-- Clientes Suspendidos -->
          <div class="metric-card jc-center">
            <div class="metric-header">
              <span class="metric-title">CLIENTES SUSPENDIDOS</span>
            </div>
            <div class="metric-body">
              <div v-if="loading" class="skeleton skeleton-text" style="width: 50px; height: 2.4rem;"></div>
              <span v-else class="metric-value text-red">{{ totalSuspensiones }}</span>
            </div>
          </div>
        </section>

        <!-- SECCIÓN CLASES -->
        <section class="classes-section">
          <div class="section-header">
            <h3>Próximas Clases de Hoy</h3>
            <router-link to="/clases" class="view-all-link">Ver Agenda Completa</router-link>
          </div>
          <div class="classes-grid">
            <!-- Skeletons para las clases -->
            <template v-if="loading">
              <div v-for="i in 2" :key="'sk-clase-' + i" class="class-card">
                <div class="class-info-main">
                  <div class="skeleton skeleton-text" style="width: 70%; height: 1.2rem; margin-bottom: 8px;"></div>
                  <div class="skeleton skeleton-text" style="width: 40%; height: 0.9rem;"></div>
                </div>
                <div class="class-meta">
                  <div class="skeleton" style="width: 80px; height: 22px; border-radius: 6px;"></div>
                  <div class="skeleton" style="width: 60px; height: 14px;"></div>
                </div>
              </div>
            </template>

            <!-- Data Real -->
            <template v-else>
              <div v-for="clase in proximasClasesFiltradas" :key="clase.id" class="class-card" :class="{ 'border-red': clase.booked_count >= clase.capacity }">
                <div class="class-info-main">
                  <h4>{{ clase.activity_name }}</h4>
                  <p class="instructor">{{ clase.court || 'No asignada' }}</p>
                </div>
                <div class="class-meta">
                  <span class="time-tag">HOY • {{ clase.template.start_time }}</span>
                  <div class="spots-status">
                    <span v-if="clase.booked_count >= clase.capacity" class="text-red font-bold">COMPLETO</span>
                    <span v-else class="spots-text">{{ clase.booked_count }}/{{ clase.capacity }} cupos</span>
                    <div class="spots-indicator-bar">
                      <div class="fill" :class="{ 'bg-red': clase.booked_count >= clase.capacity, 'bg-green': (clase.booked_count / clase.capacity) < 0.8 }" :style="{ width: (clase.booked_count / clase.capacity) * 100 + '%' }"></div>
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

      <!-- SECCIÓN HISTORIAL (ASIDE) -->
      <aside class="activity-column">
        <div class="activity-card-container">
          <div class="activity-header">
            <span class="live-dot"></span>
            <h3>Historial de Actividad</h3>
          </div>
          <div class="activity-timeline-minimal">
            <!-- Skeletons Historial -->
            <template v-if="loading">
              <div v-for="i in 3" :key="'sk-act-' + i" class="timeline-node-item">
                <div class="dot" style="background: #e2e8f0;"></div>
                <div class="node-content" style="width: 100%;">
                  <div class="skeleton skeleton-text" style="width: 90%; height: 0.9rem; margin-bottom: 6px;"></div>
                  <div class="skeleton skeleton-text" style="width: 30%; height: 0.75rem;"></div>
                </div>
              </div>
            </template>

            <!-- Data Real -->
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

      <!-- SECCIÓN EMPLEADOS -->
      <section class="staff-section">
        <div class="section-header">
          <h3>Empleados</h3>
          <span v-if="!loading" class="staff-count-badge">{{ staffEquipo.length }} Activos</span>
        </div>
        <div class="staff-grid">
          <!-- Skeletons Staff -->
          <template v-if="loading">
            <div v-for="i in 3" :key="'sk-staff-' + i" class="staff-member-card">
              <div class="skeleton" style="width: 40px; height: 40px; border-radius: 50%;"></div>
              <div class="skeleton skeleton-text" style="width: 80px; height: 1rem;"></div>
            </div>
          </template>

          <!-- Data Real -->
          <template v-else>
            <div v-for="miembro in staffEquipo" :key="miembro.id" class="staff-member-card">
              <div class="staff-avatar">{{ miembro.iniciales }}</div>
              <div class="staff-details">
                <h4>{{ miembro.nombre }}</h4>
              </div>
            </div>
          </template>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useAppClockStore } from '../stores/appClock'

// Control de carga general
const loading = ref(true)
const clock = useAppClockStore()

// Estados reactivos
const reservasHoy = ref(0)
const totalAbonosActivos = ref(0)
const totalSuspensiones = ref(0)
const staffEquipo = ref([])
const historialActividad = ref([])
const todasLasClasesDelDia = ref([])
const proximasClasesFiltradas = ref([])
let intervaloActualizacion = null

// Desacoplamos el procesamiento local de las clases del fetch puro de red
const procesarFiltroClases = () => {
  reservasHoy.value = todasLasClasesDelDia.value.reduce((acumulador, clase) => {
    return acumulador + (clase.booked_count || 0)
  }, 0)

  const ahora = new Date()
  const horaActualStr = ahora.toTimeString().slice(0, 5)

  proximasClasesFiltradas.value = todasLasClasesDelDia.value
    .filter(clase => clase.template.start_time >= horaActualStr)
    .slice(0, 4)
}

const inicializarDashboard = async () => {
  loading.value = true
  try {
    // 🚀 PARALELIZACIÓN EXPLICITA: Ambas peticiones viajan al mismo tiempo en la red
    const [resSummary, resShifts] = await Promise.all([
      axios.get('/dashboard/summary'),
      axios.get('/shifts/instances')
    ])

    // Asignar datos de /dashboard/summary
    totalAbonosActivos.value = resSummary.data.active_subscriptions
    totalSuspensiones.value = resSummary.data.suspended_clients
    staffEquipo.value = resSummary.data.staff
    historialActividad.value = resSummary.data.activity_feed

    // Asignar y procesar datos de /shifts/instances
    const hoyStr = clock.effectiveTodayStr
    todasLasClasesDelDia.value = resShifts.data.filter(clase => clase.date === hoyStr)
    
    procesarFiltroClases()

  } catch (error) {
    console.error("Error cargando el dashboard:", error)
  } finally {
    loading.value = false // Apaga los skeletons pase lo que pase
  }
}

onMounted(() => {
  inicializarDashboard()

  // El intervalo solo recalcula los filtros locales de hora, no vuelve a pegarle a la API sin necesidad
  intervaloActualizacion = setInterval(() => {
    procesarFiltroClases()
  }, 60000)
})

onUnmounted(() => {
  if (intervaloActualizacion) clearInterval(intervaloActualizacion)
})
</script>

<style scoped>
/* --- Tus estilos base se mantienen intactos --- */
.dashboard-layout { padding: 24px; max-width: 1400px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; font-family: system-ui, -apple-system, sans-serif; }
.club-banner { position: relative; height: 280px; border-radius: 20px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
.banner-bg-img { width: 100%; height: 100%; object-fit: cover; object-position: center 40%; }
.banner-overlay { position: absolute; inset: 0; background: linear-gradient(to top, rgba(0, 0, 0, 0.65) 0%, rgba(0, 0, 0, 0.15) 100%); z-index: 1; }
.banner-content { position: absolute; bottom: 28px; left: 32px; color: white; z-index: 2; }
.banner-content h1 { margin: 0; font-size: 2.2rem; font-weight: 800; text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5); }
.dashboard-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; }
.main-column { display: flex; flex-direction: column; gap: 24px; }
.metrics-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.metric-card { background: white; border: 1px solid #e1e6eb; border-radius: 16px; padding: 24px; display: flex; flex-direction: column; justify-content: space-between; min-height: 140px; }
.jc-center { justify-content: center !important; }
.metric-header { display: flex; justify-content: space-between; align-items: center; }
.metric-title { font-size: 0.75rem; font-weight: 700; color: #718096; letter-spacing: 0.5px; }
.metric-body { display: flex; align-items: baseline; gap: 10px; margin-top: 12px; }
.metric-value { font-size: 2.4rem; font-weight: 800; color: #1a202c; }
.text-green { color: #48bb78 !important; }
.text-red { color: #e53e3e !important; }
.text-green-change { color: #48bb78; font-size: 0.85rem; font-weight: 600; }
.mini-bar-chart { display: flex; align-items: flex-end; gap: 6px; height: 24px; margin-top: 12px; }
.mini-bar-chart .bar { flex: 1; background: #edf2f7; border-radius: 2px; }
.classes-section { background: white; border: 1px solid #e1e6eb; border-radius: 16px; padding: 24px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.section-header h3 { margin: 0; font-size: 1.15rem; color: #1a202c; font-weight: 700; }
.view-all-link { color: #2d658d; font-size: 0.85rem; text-decoration: none; font-weight: 600; }
.view-all-link:hover { text-decoration: underline; }
.classes-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.class-card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; background: #ffffff; display: flex; flex-direction: column; justify-content: space-between; gap: 16px; }
.class-card h4 { margin: 0 0 4px 0; font-size: 1.05rem; color: #1a202c; }
.instructor { margin: 0; font-size: 0.85rem; color: #718096; }
.class-meta { display: flex; justify-content: space-between; align-items: center; }
.time-tag { background: #edf2f7; padding: 4px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; color: #4a5568; }
.spots-status { text-align: right; }
.spots-text { font-size: 0.8rem; color: #4a5568; display: block; margin-bottom: 4px; }
.spots-indicator-bar { width: 80px; height: 4px; background: #edf2f7; border-radius: 2px; overflow: hidden; display: inline-block; }
.spots-indicator-bar .fill { height: 100%; background: #2d658d; }
.no-data-placeholder { grid-column: span 2; padding: 30px; text-align: center; color: #718096; font-size: 0.9rem; }
.activity-column { grid-column: 2; }
.activity-card-container { background: white; border: 1px solid #e1e6eb; border-radius: 16px; padding: 24px; height: 100%; }
.activity-header { display: flex; align-items: center; gap: 8px; margin-bottom: 24px; }
.activity-header h3 { margin: 0; font-size: 1.15rem; color: #1a202c; }
.live-dot { width: 8px; height: 8px; background: #48bb78; border-radius: 50%; }
.activity-timeline-minimal { display: flex; flex-direction: column; gap: 24px; position: relative; padding-left: 8px; }
.activity-timeline-minimal::before { content: ''; position: absolute; left: 12px; top: 8px; bottom: 8px; width: 2px; background: #edf2f7; }
.timeline-node-item { display: flex; gap: 16px; align-items: flex-start; position: relative; }
.dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 5px; z-index: 1; box-shadow: 0 0 0 4px white; }
.orange-dot { background-color: #ff6f00; }
.node-content p { margin: 0; font-size: 0.88rem; color: #2d3748; line-height: 1.4; }
.node-time { font-size: 0.78rem; color: #9ab0c5; display: block; margin-top: 2px; }
.staff-section { grid-column: span 2; background: white; border: 1px solid #e1e6eb; border-radius: 16px; padding: 24px; }
.staff-count-badge { background: #e8f5e9; color: #48bb78; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; }
.staff-grid { display: flex; flex-wrap: wrap; gap: 24px; margin-top: 16px; }
.staff-member-card { display: flex; align-items: center; gap: 12px; background: #f8fafc; padding: 12px 20px; border-radius: 12px; border: 1px solid #e2e8f0; min-width: 180px; }
.staff-avatar { width: 40px; height: 40px; background: #e2f0fd; color: #2d658d; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; flex-shrink: 0; }
.staff-details h4 { margin: 0; font-size: 0.95rem; color: #1a202c; font-weight: 600; }
.font-bold { font-weight: 700; }
.border-red { border-color: #fecaca; }
.bg-red { background-color: #e53e3e !important; }
.bg-green { background-color: #48bb78 !important; }

/* --- 🌟 NUEVOS ESTILOS PARA EL SKELETON ANIMADO 🌟 --- */
.skeleton {
  background: linear-gradient(90deg, #f0f2f5 25%, #e6e8ec 50%, #f0f2f5 75%);
  background-size: 200% 100%;
  animation: loading-shimmer 1.4s infinite ease-in-out;
  border-radius: 4px;
  display: inline-block;
}
.skeleton-text {
  height: 1em;
  margin-bottom: 4px;
}
@keyframes loading-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 900px) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .activity-column { grid-column: 1; }
  .staff-section { grid-column: 1; }
  .metrics-row { grid-template-columns: 1fr; }
  .classes-grid { grid-template-columns: 1fr; }
}
</style>
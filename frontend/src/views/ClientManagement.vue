<template>
  <div class="page">
    <div class="gestion-container">
      <header class="page-header">
        <h1>Gestión de clientes</h1>
        <p>Panel de administración de clientes, estados de cuenta y reservas</p>
      </header>

      <div class="filters-card">
        <div class="filter-group search-group">
          <label>Buscar cliente</label>
          <input type="text" v-model="filterSearch" placeholder="Ingresá nombre o DNI..." />
        </div>
        <div class="filter-group">
          <label>Filtrar por estado</label>
          <select v-model="filterStatus">
            <option value="">Todos los estados</option>
            <option value="Activo">Activo</option>
            <option value="Suspendido">Suspendido</option>
          </select>
        </div>
        <div class="actions-group">
          <button @click="resetFilters" class="btn-clear">Limpiar</button>
          <button @click="showCreateModal = true" class="btn-primary-action">+ Nuevo Cliente</button>
        </div>
      </div>

      <div class="table-container">
        <table class="shifts-table">
          <thead>
            <tr>
              <th>Nombre y Apellido</th>
              <th>DNI</th>
              <th>Estado</th>
              <th class="text-center">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="cliente in filteredClientes" :key="cliente.id">
              <tr :class="{ 'row-suspended': cliente.estado === 'Suspendido' }">
                <td><span class="client-name">{{ cliente.nombre }}</span></td>
                <td>{{ cliente.dni }}</td>
                <td>
                  <span class="status-badge" :class="cliente.estado.toLowerCase()">{{ cliente.estado }}</span>
                </td>
                <td class="actions-cell justify-center">
                  <button
                    @click="toggleAccordion(cliente.id)"
                    class="icon-btn"
                    :class="{ 'rotate-arrow': activeAccordion === cliente.id }"
                    title="Ver operaciones"
                  >
                    {{ activeAccordion === cliente.id ? '▲' : '▼' }}
                  </button>
                  <div class="dropdown-wrapper">
                    <button @click.stop="toggleDropdown(cliente.id)" class="icon-btn" title="Más opciones">⋮</button>
                    <div v-if="activeDropdown === cliente.id" class="dropdown-menu dropdown-right">
                      <button @click="editCliente(cliente)">✏️ Editar Datos</button>
                      <button @click="deleteCliente(cliente)" class="btn-delete-option">🗑️ Eliminar cliente</button>
                    </div>
                  </div>
                </td>
              </tr>

              <tr v-if="activeAccordion === cliente.id" class="accordion-row">
                <td colspan="4">
                  <div class="accordion-content">
                    <div class="accordion-header">
                      <h4>Operaciones asociadas a: <span>{{ cliente.nombre }}</span></h4>
                    </div>
                    <div class="accordion-actions">
                      <button @click="createReserva(cliente)" class="btn-nested">Nueva reserva</button>
                      <button @click="createAbono(cliente)" class="btn-nested"> Nuevo abono</button>
                      <button @click="viewReservas(cliente)" class="btn-nested"> Historial reservas</button>
                      <button @click="viewPagos(cliente)" class="btn-nested"> Ver pagos</button>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <div v-if="filteredClientes.length === 0" class="empty-state">
          No se encontraron clientes con los criterios de búsqueda.
        </div>
      </div>
    </div>

    <transition name="fade">
      <div v-if="showCreateModal" class="modal-overlay">
        <div class="modal-card form-modal-card">
          <header class="form-header">
            <h3>Registrar cliente</h3>
            <p>Crea una cuenta para un nuevo cliente desde el panel.</p>
          </header>
          <form @submit.prevent="handleSubmitForm" class="equipo-form">
            <div class="form-grid">
              <div class="input-group">
                <label>Nombre</label>
                <input v-model="form.first_name" type="text" required />
              </div>
              <div class="input-group">
                <label>Apellido</label>
                <input v-model="form.last_name" type="text" required />
              </div>
            </div>
            <div class="input-group">
              <label>DNI (sin puntos)</label>
              <input v-model="form.dni" type="text" required />
            </div>
            <div class="input-group">
              <label>Correo electrónico</label>
              <input v-model="form.email" type="email" required />
            </div>
            <div class="input-group">
              <label>Contraseña</label>
              <input v-model="form.password" type="password" required />
            </div>
            <div class="modal-actions-container">
              <button type="submit" class="btn-confirm" :disabled="loadingForm">
                <span v-if="loadingForm" class="spinner-inline"></span>
                <span v-else>Crear cliente</span>
              </button>
              <button type="button" @click="closeCreateModal" class="btn-cancel" :disabled="loadingForm">Cancelar</button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="showReservaModal" class="modal-overlay" @click.self="showReservaModal = false">
        <div class="modal-card modal-large">
          <header class="form-header">
            <h3>Nueva Reserva</h3>
            <p>Reservando clase para: <strong>{{ clienteSeleccionado?.nombre }}</strong></p>
          </header>

          <div class="modal-filters">
            <div class="input-group">
              <label>Actividad</label>
              <select v-model="filterActividad" @change="fetchInstancias">
                <option value="">Todas</option>
                <option v-for="act in actividades" :key="act.id" :value="act.id">{{ act.name }}</option>
              </select>
            </div>
            <div class="input-group">
              <label>Día</label>
              <select v-model="filterDia" @change="fetchInstancias">
                <option value="">Todos</option>
                <option v-for="dia in diasSemana" :key="dia" :value="dia">{{ dia }}</option>
              </select>
            </div>
          </div>

          <div class="instancias-list">
            <div v-if="loadingInstancias" class="empty-state">Cargando turnos...</div>
            <div v-else-if="instancias.length === 0" class="empty-state">No hay turnos disponibles.</div>
            <div
              v-for="inst in instancias"
              :key="inst.instance_id"
              class="instancia-item"
              :class="{ selected: instanciaSeleccionada?.instance_id === inst.instance_id }"
              @click="selectInstancia(inst)"
            >
              <div class="instancia-info">
                <span class="instancia-actividad">{{ inst.activity_name }}</span>
                <span class="instancia-detalle">{{ inst.date }} · {{ inst.day_of_week }} {{ inst.start_time }}</span>
              </div>
              <div class="instancia-right">
                <span class="instancia-precio">${{ inst.price }}</span>
                <span class="instancia-cupos">{{ inst.cupos_disponibles }} cupos</span>
              </div>
            </div>
          </div>

          <div v-if="instanciaSeleccionada" class="pago-section">
            <p class="pago-label">Seleccioná el monto a cobrar:</p>
            <div class="pago-botones">
              <button
                class="btn-pago-opcion"
                :class="{ active: amountPaid === precioMinimo }"
                @click="amountPaid = precioMinimo"
              >
                50% — ${{ precioMinimo }}
              </button>
              <button
                class="btn-pago-opcion"
                :class="{ active: amountPaid === instanciaSeleccionada.price }"
                @click="amountPaid = instanciaSeleccionada.price"
              >
                100% — ${{ instanciaSeleccionada.price }}
              </button>
            </div>
          </div>

          <div class="modal-actions-container">
            <button class="btn-confirm" @click="submitReserva" :disabled="loadingReserva || !instanciaSeleccionada || amountPaid === 0">
              {{ loadingReserva ? 'Guardando...' : 'Confirmar Reserva' }}
            </button>
            <button class="btn-cancel" @click="showReservaModal = false">Cancelar</button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="showAbonoModal" class="modal-overlay" @click.self="showAbonoModal = false">
        <div class="modal-card modal-large">
          <header class="form-header">
            <h3>Registrar Abono</h3>
            <p>Abono mensual para: <strong>{{ clienteSeleccionado?.nombre }}</strong></p>
          </header>

          <div class="modal-filters">
            <div class="input-group">
              <label>Actividad</label>
              <select v-model="filterAbonoActividad" @change="filtrarTemplates">
                <option value="">Todas</option>
                <option v-for="act in actividadesAbono" :key="act.id" :value="act.id">{{ act.name }}</option>
              </select>
            </div>
            <div class="input-group">
              <label>Día</label>
              <select v-model="filterAbonoDia" @change="filtrarTemplates">
                <option value="">Todos</option>
                <option v-for="dia in diasSemana" :key="dia" :value="dia">{{ dia }}</option>
              </select>
            </div>
          </div>

          <div class="instancias-list">
            <div v-if="loadingTemplates" class="empty-state">Cargando horarios...</div>
            <div v-else-if="templatesFiltrados.length === 0" class="empty-state">No hay horarios disponibles.</div>
            <div
              v-for="tmpl in templatesFiltrados"
              :key="tmpl.id"
              class="instancia-item"
              :class="{ selected: templateSeleccionado?.id === tmpl.id }"
              @click="templateSeleccionado = tmpl"
            >
              <div class="instancia-info">
                <span class="instancia-actividad">{{ tmpl.activity_name }}</span>
                <span class="instancia-detalle">{{ tmpl.day_of_week }} · {{ tmpl.start_time }}</span>
              </div>
              <div class="instancia-right">
                <span class="instancia-precio">${{ tmpl.price }}/clase</span>
                <span class="instancia-cupos">{{ tmpl.capacity }} cupos</span>
              </div>
            </div>
          </div>

          <div v-if="templateSeleccionado" class="pago-section">
            <p class="pago-label">Seleccioná el tipo de abono:</p>
            <div class="pago-botones">
              <button
                class="btn-pago-opcion"
                :class="{ active: tipoAbono === 'completo' }"
                @click="tipoAbono = 'completo'"
              >
                Mes completo — ${{ Math.round(templateSeleccionado.price * 4 * 100) / 100 }}
              </button>
              <button
                class="btn-pago-opcion"
                :class="{ active: tipoAbono === 'mitad' }"
                @click="tipoAbono = 'mitad'"
              >
                Mitad de mes — ${{ Math.round(templateSeleccionado.price * 4 * 0.8 * 100) / 100 }}
              </button>
            </div>
          </div>

          <div v-if="templateSeleccionado" class="resumen-pago">
            Total a cobrar: <strong>${{ precioAbono }}</strong>
          </div>

          <div class="modal-actions-container">
            <button class="btn-confirm" @click="submitAbono" :disabled="loadingAbono || !templateSeleccionado">
              {{ loadingAbono ? 'Guardando...' : 'Confirmar Abono' }}
            </button>
            <button class="btn-cancel" @click="showAbonoModal = false">Cancelar</button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="showReservasModal" class="modal-overlay" @click.self="showReservasModal = false">
        <div class="modal-card modal-large">
          <header class="form-header">
            <h3>Historial de Reservas</h3>
            <p>Clases de: <strong>{{ clienteSeleccionado?.nombre }}</strong></p>
          </header>

          <div class="instancias-list">
            <div v-if="loadingReservas" class="empty-state">Cargando reservas...</div>
            <div v-else-if="reservasCliente.length === 0" class="empty-state">No hay reservas registradas.</div>

            <div v-for="b in reservasCliente" :key="b.booking_id" class="reserva-item">
              <div class="reserva-info">
                <div class="reserva-top">
                  <span class="instancia-actividad">{{ b.activity_name }}</span>
                  <span class="reserva-badge" :class="b.status.toLowerCase()">{{ b.status }}</span>
                </div>
                <span class="instancia-detalle">{{ b.date }} · {{ b.day_of_week }} {{ b.start_time }}</span>
                <div class="reserva-pago-info">
                  <span v-if="b.is_subscription" class="tag-abono">Abono</span>
                  <span v-else class="tag-suelta">Clase suelta</span>
                  <span v-if="!b.is_subscription">
                    Pagado: <strong>${{ b.amount_paid }}</strong> de ${{ b.price }}
                    <span class="pago-tag" :class="b.payment_status">
                      {{ b.payment_status === 'paid' ? '✓ Completo' : '⏳ Seña' }}
                    </span>
                  </span>
                </div>
              </div>

              <button
                v-if="!b.is_subscription && b.payment_status === 'partial' && b.status !== 'Cancelled'"
                class="btn-pagar-restante"
                :disabled="loadingPago[b.booking_id]"
                @click="pagarRestante(b)"
              >
                {{ loadingPago[b.booking_id] ? '...' : `Cobrar $${b.price - b.amount_paid}` }}
              </button>
            </div>
          </div>

          <div class="modal-actions-container">
            <button class="btn-cancel" style="flex: 0 0 auto; padding: 12px 30px;" @click="showReservasModal = false">Cerrar</button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="showPagosModal" class="modal-overlay" @click.self="showPagosModal = false">
        <div class="modal-card modal-large">
          <header class="form-header">
            <h3>Historial de Pagos</h3>
            <p>Cuenta corriente de: <strong>{{ clienteSeleccionado?.nombre }}</strong></p>
          </header>

          <div class="instancias-list">
            <div v-if="loadingPagos" class="empty-state">Cargando pagos...</div>
            <div v-else-if="pagosCliente.length === 0" class="empty-state">No hay pagos registrados.</div>

            <div v-for="p in pagosCliente" :key="p.payment_id" class="reserva-item">
              <div class="reserva-info">
                <div class="reserva-top">
                  <span class="instancia-actividad">${{ p.amount.toFixed(2) }}</span>
                  <span class="tag-abono" v-if="p.type === 'subscription'">Abono</span>
                  <span class="tag-suelta" v-else>Clase suelta</span>
                </div>
                <span class="instancia-detalle">{{ new Date(p.date).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
              </div>
              <span class="pago-tag" :class="p.status === 'completed' || p.status === 'paid' ? 'paid' : 'partial'">
                {{ p.status === 'completed' || p.status === 'paid' ? '✓ Completo' : '⏳ Seña' }}
              </span>
            </div>
          </div>

          <div class="resumen-pago">
            Total abonado: <strong>${{ totalPagado }}</strong>
          </div>

          <div class="modal-actions-container">
            <button class="btn-cancel" style="flex: 0 0 auto; padding: 12px 30px;" @click="showPagosModal = false">Cerrar</button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="toastMessage" :class="['alert-toast', toastType]">{{ toastMessage }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../utils/api' // 🌟 CORRECCIÓN: Usamos el cliente HTTP unificado del club para los tokens

// ---- Filtros ----
const filterSearch = ref('')
const filterStatus = ref('')

// ---- Modales y loadings generales ----
const showCreateModal = ref(false)
const loadingForm = ref(false)
const activeDropdown = ref(null)
const activeAccordion = ref(null)

// ---- Toast ----
const toastMessage = ref('')
const toastType = ref('')
const showToast = (msg, type) => {
  toastMessage.value = msg
  toastType.value = type
  setTimeout(() => { toastMessage.value = '' }, 3000)
}

// ---- Formulario nuevo cliente ----
const form = ref({ first_name: '', last_name: '', dni: '', email: '', password: '' })

// ---- Clientes ----
const clientes = ref([])

const fetchClientes = async () => {
  try {
    const res = await api.get('/admin/clientes')
    clientes.value = res.data.sort((a, b) => b.id - a.id)
  } catch (e) {
    showToast('Error al cargar el listado de clientes.', 'error')
  }
}

const filteredClientes = computed(() => {
  return clientes.value.filter(c => {
    const searchLower = filterSearch.value.toLowerCase().trim()
    if (!searchLower) return !filterStatus.value || c.estado === filterStatus.value
    const matchNombre = c.nombre?.toLowerCase().includes(searchLower)
    const matchDni = c.dni?.startsWith(searchLower)
    const matchStatus = !filterStatus.value || c.estado === filterStatus.value
    return (matchNombre || matchDni) && matchStatus
  })
})

const resetFilters = () => {
  filterSearch.value = ''
  filterStatus.value = ''
}

const toggleDropdown = (clienteId) => {
  activeDropdown.value = activeDropdown.value === clienteId ? null : clienteId
}

const toggleAccordion = (clienteId) => {
  activeAccordion.value = activeAccordion.value === clienteId ? null : clienteId
}

const handleSubmitForm = async () => {
  loadingForm.value = true
  try {
    const res = await api.post('/admin/crear-cliente', form.value)
    const nuevoCliente = {
      id: res.data?.id_user || res.data?.id || Date.now(),
      nombre: `${form.value.first_name.trim()} ${form.value.last_name.trim()}`,
      dni: form.value.dni,
      estado: 'Activo'
    }
    clientes.value.unshift(nuevoCliente)
    showToast('Cliente creado con éxito.', 'success')
    closeCreateModal()
  } catch (error) {
    showToast(error.response?.data?.detail || 'Error al guardar el cliente.', 'error')
  } finally {
    loadingForm.value = false
  }
}

const closeCreateModal = () => {
  showCreateModal.value = false
  form.value = { first_name: '', last_name: '', dni: '', email: '', password: '' }
}

const editCliente = (cliente) => alert(`Editar datos de: ${cliente.nombre}`)
const viewReservas = (cliente) => openReservasModal(cliente)
const viewPagos = (cliente) => openPagosModal(cliente)
const deleteCliente = (cliente) => {
  if (confirm(`¿Estás seguro de que querés eliminar permanentemente a ${cliente.nombre}?`)) {
    alert(`Eliminando a: ${cliente.nombre}`)
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('click', () => { activeDropdown.value = null })
}

// ---- Nueva Reserva ----
const showReservaModal = ref(false)
const clienteSeleccionado = ref(null)
const instancias = ref([])
const actividades = ref([])
const filterActividad = ref('')
const filterDia = ref('')
const instanciaSeleccionada = ref(null)
const amountPaid = ref(0)
const loadingInstancias = ref(false)
const fontLoadingReserva = ref(false)
const loadingReserva = ref(false)
const diasSemana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

const fetchActividades = async () => {
  try {
    const res = await api.get('/activities')
    actividades.value = res.data
  } catch (e) {
    showToast('Error al cargar actividades.', 'error')
  }
}

const fetchInstancias = async () => {
  if (!clienteSeleccionado.value) return
  loadingInstancias.value = true
  try {
    const params = {}
    if (filterActividad.value) params.activity_id = filterActividad.value
    if (filterDia.value) params.day_of_week = filterDia.value
    const res = await api.get(`/admin/clientes/${clienteSeleccionado.value.id}/instancias-disponibles`, { params })
    instancias.value = res.data
  } catch (e) {
    showToast('Error al cargar instancias.', 'error')
  } finally {
    loadingInstancias.value = false
  }
}

const openReservaModal = async (cliente) => {
  clienteSeleccionado.value = cliente
  instanciaSeleccionada.value = null
  amountPaid.value = 0
  filterActividad.value = ''
  filterDia.value = ''
  showReservaModal.value = true
  await fetchActividades()
  await fetchInstancias()
}

const selectInstancia = (inst) => {
  instanciaSeleccionada.value = inst
  amountPaid.value = 0
}

const precioMinimo = computed(() => {
  if (!instanciaSeleccionada.value) return 0
  return Math.round(instanciaSeleccionada.value.price * 0.5 * 100) / 100
})

// 🌟 ARREGLO DEL FLUJO: Ruta apuntada al endpoint vivo de reservas del sistema
const submitReserva = async () => {
  if (!instanciaSeleccionada.value) return showToast('Seleccioná una instancia.', 'error')
  if (amountPaid.value === 0) return showToast('Seleccioná el monto a cobrar.', 'error')

  loadingReserva.value = true
  try {
    // 🚀 Lógica alineada con la API de FastAPI para reservar clases sueltas
    await api.post('/bookings/', {
      instance_id: Number(instanciaSeleccionada.value.instance_id),
      subscription_id: null
    })

    showToast('Reserva creada con éxito.', 'success')
    showReservaModal.value = false // Cierre automático exitoso de la UI
  } catch (e) {
    showToast(e.response?.data?.detail || 'Error al crear la reserva.', 'error')
  } finally {
    loadingReserva.value = false
  }
}

const createReserva = (cliente) => openReservaModal(cliente)

// ---- Nuevo Abono ----
const showAbonoModal = ref(false)
const templates = ref([])
const templatesFiltrados = ref([])
const actividadesAbono = ref([])
const templateSeleccionado = ref(null)
const tipoAbono = ref('completo')
const loadingTemplates = ref(false)
const loadingAbono = ref(false)
const filterAbonoActividad = ref('')
const filterAbonoDia = ref('')

const fetchTemplates = async () => {
  loadingTemplates.value = true
  try {
    const res = await api.get('/activities')
    const allTemplates = []
    res.data.forEach(act => {
      act.templates?.forEach(tmpl => {
        if (tmpl.is_active !== false) {
          allTemplates.push({ ...tmpl, activity_name: act.name, activity_id: act.id })
        }
      })
    })
    templates.value = allTemplates
    actividadesAbono.value = res.data.map(act => ({ id: act.id, name: act.name }))
    filtrarTemplates()
  } catch (e) {
    showToast('Error al cargar los horarios.', 'error')
  } finally {
    loadingTemplates.value = false
  }
}

const filtrarTemplates = () => {
  templateSeleccionado.value = null
  templatesFiltrados.value = templates.value.filter(tmpl => {
    const matchActividad = !filterAbonoActividad.value || tmpl.activity_id === filterAbonoActividad.value
    const matchDia = !filterAbonoDia.value || tmpl.day_of_week === filterAbonoDia.value
    return matchActividad && matchDia
  })
}

const openAbonoModal = async (cliente) => {
  clienteSeleccionado.value = cliente
  templateSeleccionado.value = null
  tipoAbono.value = 'completo'
  filterAbonoActividad.value = ''
  filterAbonoDia.value = ''
  showAbonoModal.value = true
  await fetchTemplates()
}
const precioAbono = computed(() => {
  if (!templateSeleccionado.value) return 0
  const base = templateSeleccionado.value.price * 4
  return tipoAbono.value === 'mitad'
    ? Math.round(base * 0.8 * 100) / 100
    : Math.round(base * 100) / 100
})

const submitAbono = async () => {
  if (!templateSeleccionado.value) return showToast('Seleccioná un horario.', 'error')
  loadingAbono.value = true
  try {
    await api.post(`/admin/clientes/${clienteSeleccionado.value.id}/registrar-abono`, {
      template_id: templateSeleccionado.value.id,
      tipo: tipoAbono.value,
    })
    showToast('Abono registrado con éxito.', 'success')
    showAbonoModal.value = false
  } catch (e) {
    showToast(e.response?.data?.detail || 'Error al registrar el abono.', 'error')
  } finally {
    loadingAbono.value = false
  }
}

const createAbono = (cliente) => openAbonoModal(cliente)

// ---- Historial Reservas ----
const showReservasModal = ref(false)
const reservasCliente = ref([])
const loadingReservas = ref(false)
const loadingPago = ref({})

const fetchReservasCliente = async (cliente) => {
  loadingReservas.value = true
  try {
    const res = await api.get(`/admin/clientes/${cliente.id}/reservas`)
    reservasCliente.value = res.data
  } catch (e) {
    showToast('Error al cargar las reservas.', 'error')
  } finally {
    loadingReservas.value = false
  }
}

const openReservasModal = async (cliente) => {
  clienteSeleccionado.value = cliente
  showReservasModal.value = true
  await fetchReservasCliente(cliente)
}

const pagarRestante = async (booking) => {
  loadingPago.value[booking.booking_id] = true
  try {
    await api.patch(`/admin/clientes/${clienteSeleccionado.value.id}/reservas/${booking.booking_id}/pagar-restante`)
    booking.payment_status = 'paid'
    booking.amount_paid = booking.price
    showToast('Pago completado correctamente.', 'success')
  } catch (e) {
    showToast(e.response?.data?.detail || 'Error al registrar el pago.', 'error')
  } finally {
    loadingPago.value[booking.booking_id] = false
  }
}

// ---- Ver Pagos ----
const showPagosModal = ref(false)
const pagosCliente = ref([])
const loadingPagos = ref(false)

const fetchPagosCliente = async (cliente) => {
  loadingPagos.value = true
  try {
    const res = await api.get(`/admin/clientes/${cliente.id}/pagos`)
    pagosCliente.value = res.data
  } catch (e) {
    showToast('Error al cargar los pagos.', 'error')
  } finally {
    loadingPagos.value = false
  }
}

const openPagosModal = async (cliente) => {
  clienteSeleccionado.value = cliente
  showPagosModal.value = true
  await fetchPagosCliente(cliente)
}

const totalPagado = computed(() => {
  return pagosCliente.value.reduce((acc, p) => acc + p.amount, 0).toFixed(2)
})

onMounted(fetchClientes)
</script>

<style scoped>
.page {
  position: relative;
  min-height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  background: #ffffff;
  font-family: 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
}

.page::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 300px;
  background: #2d658d;
  z-index: 0;
}

.gestion-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 40px;
  align-items: center;
}

.page-header { text-align: center; margin-bottom: 10px; }
.page-header h1 { margin: 0 0 8px; font-size: 28px; color: #ffffff; font-weight: 800; }
.page-header p { margin: 0; color: #e2e8f0; font-size: 15px; }

.filters-card {
  width: 100%;
  background: white;
  padding: 30px;
  border-radius: 18px;
  display: flex;
  gap: 20px;
  align-items: flex-end;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.15);
  box-sizing: border-box;
}

.filter-group { display: flex; flex-direction: column; gap: 6px; flex: 1; }
.search-group { flex: 2; }
.filter-group label { display: block; font-size: 12px; font-weight: 600; color: #374151; }

input, select {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  background: #ffffff;
  color: #111827;
  font-size: 15px;
  outline: none;
  box-sizing: border-box;
  height: 42px;
}

input:focus { border-color: #2d658d; }

.actions-group { display: flex; gap: 12px; align-items: center; }

.btn-clear {
  display: flex; align-items: center; justify-content: center;
  background: #f1f0f0; color: #2d658d; border: 1px solid #f4f4f4;
  padding: 10px 20px; border-radius: 10px; font-weight: 700; font-size: 14px;
  cursor: pointer; height: 42px; text-transform: uppercase;
  transition: all 0.2s ease; white-space: nowrap;
}
.btn-clear:hover { background: #2d658d; color: rgb(218, 217, 217); border-color: #f1f1f1; }

.btn-primary-action {
  display: flex; align-items: center; justify-content: center;
  background: #2d658d; color: white; border: none;
  padding: 10px 20px; border-radius: 10px; font-weight: 700; font-size: 14px;
  cursor: pointer; height: 42px; text-transform: uppercase;
  transition: opacity 0.2s, transform 0.2s; white-space: nowrap;
  box-shadow: 0 4px 12px rgba(255, 111, 0, 0.2);
}
.btn-primary-action:hover { opacity: 0.9; transform: translateY(-1px); }

.table-container {
  width: 100%; background: white; padding: 30px; border-radius: 18px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.05); overflow-x: auto; box-sizing: border-box;
}

.shifts-table { width: 100%; border-collapse: collapse; text-align: left; }
.shifts-table th {
  padding: 12px; border-bottom: 2px solid #f3f4f6;
  color: #6b7280; font-size: 13px; text-transform: uppercase; font-weight: 800;
}
.shifts-table td {
  padding: 15px 12px; border-bottom: 1px solid #f9fafb;
  color: #374151; font-size: 14px; vertical-align: middle;
}

.client-name { font-weight: 700; color: #111827; }
.row-suspended { background: #fffdfd; }
.row-suspended .client-name { color: #9ca3af; text-decoration: line-through; opacity: 0.6; }

.status-badge {
  padding: 4px 10px; border-radius: 20px; font-size: 11px;
  font-weight: 700; display: inline-block; text-transform: uppercase;
}
.status-badge.activo { background: #e6f4ea; color: #137333; }
.status-badge.suspendido { background: #fce8e6; color: #c5221f; }

.actions-cell { display: flex; gap: 20px; align-items: center; }
.text-center { text-align: center; }
.justify-center { justify-content: center; }

.icon-btn {
  display: inline-flex; align-items: center; justify-content: center;
  background: none; border: none; cursor: pointer;
  filter: grayscale(1); opacity: 0.4; font-size: 18px;
  transition: transform 0.2s, opacity 0.2s, filter 0.2s;
  padding: 0; min-width: 24px; min-height: 24px;
}
.icon-btn:hover:not(:disabled) { transform: scale(1.2); filter: grayscale(0); opacity: 1; }
.icon-btn:disabled { cursor: not-allowed; opacity: 0.6; }

.accordion-row { background: #fdfefe; border-left: 4px solid #2d658d; }
.accordion-row td { padding: 0px 24px 15px 24px !important; border-bottom: 1px solid #e5e7eb !important; }

.accordion-content {
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 10px; padding: 16px 20px; animation: slideDown 0.2s ease-out;
}
.accordion-header h4 { margin: 0 0 12px 0; font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
.accordion-header h4 span { color: #1e293b; font-weight: 700; }
.accordion-actions { display: flex; gap: 12px; flex-wrap: wrap; }

.btn-nested {
  background: #ffffff; border: 1px solid #cbd5e1; color: #334155;
  padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.2s ease; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.btn-nested:hover { background: #2d658d; color: white; border-color: #2d658d; transform: translateY(-1px); }

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}

.dropdown-wrapper { position: relative; display: inline-block; }
.dropdown-menu {
  position: absolute; top: 100%; left: 0; z-index: 50;
  min-width: 160px; background-color: #ffffff; border: 1px solid #e5e7eb;
  border-radius: 8px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12);
  padding: 6px 0; margin-top: 6px; display: flex; flex-direction: column;
}
.dropdown-menu.dropdown-right { left: auto; right: 0; }
.dropdown-menu button {
  width: 100%; padding: 10px 16px; background: none; border: none;
  text-align: left; font-size: 13px; color: #374151; cursor: pointer; transition: background 0.2s;
}
.dropdown-menu button:hover { background-color: #f3f4f6; color: #111827; }
.dropdown-menu button.btn-delete-option { color: #dc2626; border-top: 1px solid #f3f4f6; }
.dropdown-menu button.btn-delete-option:hover { background-color: #fef2f2; }

.modal-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(45, 101, 141, 0.8); backdrop-filter: blur(4px);
  display: flex; justify-content: center; align-items: center; z-index: 100;
}

.modal-card {
  background: white; padding: 35px; border-radius: 18px;
  width: 90%; box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}

.form-modal-card { max-width: 480px; }

.modal-large {
  max-width: 620px;
  max-height: 85vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-header { text-align: center; margin-bottom: 25px; }
.form-header h3 { font-size: 22px; color: #111827; font-weight: 800; margin: 0; }
.form-header p { color: #6b7280; font-size: 13px; margin-top: 6px; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }

.input-group { margin-bottom: 16px; display: flex; flex-direction: column; text-align: left; }
.input-group label { font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 6px; }

.modal-actions-container { display: flex; gap: 10px; margin-top: 25px; }

.btn-confirm {
  display: inline-flex; align-items: center; justify-content: center;
  flex: 1; background: #ff6f00; color: white; border: none; padding: 12px;
  border-radius: 10px; font-weight: 700; cursor: pointer;
  text-transform: uppercase; font-size: 13px; letter-spacing: 0.5px; min-height: 43px;
}
.btn-confirm:disabled { background: #d1d5db; cursor: not-allowed; }

.btn-cancel {
  flex: 1; background: #e5e7eb; color: #374151; border: none; padding: 12px;
  border-radius: 10px; font-weight: 700; cursor: pointer;
  text-transform: uppercase; font-size: 13px;
}
.btn-cancel:hover:not(:disabled) { background: #cbd5e1; }
.btn-cancel:disabled { cursor: not-allowed; opacity: 0.6; }

.modal-filters { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.instancias-list {
  display: flex; flex-direction: column; gap: 8px;
  max-height: 280px; overflow-y: auto;
}

.instancia-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 10px;
  cursor: pointer; transition: all 0.2s;
}
.instancia-item:hover { border-color: #2d658d; background: #f0f7ff; }
.instancia-item.selected { border-color: #2d658d; background: #e8f4fd; }

.instancia-info { display: flex; flex-direction: column; gap: 4px; }
.instancia-actividad { font-weight: 700; color: #111827; font-size: 14px; }
.instancia-detalle { font-size: 12px; color: #6b7280; }

.instancia-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.instancia-precio { font-weight: 800; color: #ff6f00; font-size: 15px; }
.instancia-cupos { font-size: 11px; color: #6b7280; }

.pago-section { border-top: 1px solid #e5e7eb; padding-top: 16px; }
.pago-label { font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 8px; }

.pago-botones { display: flex; gap: 10px; margin-top: 8px; }

.btn-pago-opcion {
  flex: 1; padding: 10px; border: 1px solid #2d658d; border-radius: 8px;
  background: white; color: #2d658d; font-weight: 700; cursor: pointer;
  font-size: 13px; transition: all 0.2s;
}
.btn-pago-opcion:hover { background: #2d658d; color: white; }
.btn-pago-opcion.active { background: #2d658d; color: white; }

.resumen-pago {
  text-align: center; font-size: 15px; color: #374151;
  padding: 12px; background: #f8fafc; border-radius: 10px; border: 1px solid #e2e8f0;
}
.resumen-pago strong { color: #ff6f00; font-size: 18px; }

.spinner-inline {
  width: 18px; height: 18px; border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%; border-top-color: white; animation: spin 0.8s linear infinite;
}
.spinner-small {
  width: 14px; height: 14px; border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%; border-top-color: #374151; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.alert-toast {
  position: fixed; bottom: 20px; right: 20px; padding: 15px 25px;
  border-radius: 12px; color: white; font-weight: 600;
  box-shadow: 0 10px 20px rgba(0,0,0,0.1); z-index: 1000;
}
.success { background: #2d658d; }
.error { background: #c0392b; }

.empty-state { padding: 40px; text-align: center; color: #9ca3af; font-weight: 600; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.reserva-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  gap: 12px;
}

.reserva-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.reserva-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reserva-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
  text-transform: uppercase;
}

.reserva-badge.confirmed { background: #e6f4ea; color: #137333; }
.reserva-badge.cancelled { background: #fce8e6; color: #c5221f; }
.reserva-badge.pending { background: #fef9c3; color: #854d0e; }

.reserva-pago-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
  flex-wrap: wrap;
}

.tag-abono {
  background: #ede9fe;
  color: #5b21b6;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
  text-transform: uppercase;
}

.tag-suelta {
  background: #e0f2fe;
  color: #0369a1;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
  text-transform: uppercase;
}

.pago-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
}

.pago-tag.paid { background: #e6f4ea; color: #137333; }
.pago-tag.partial { background: #fef9c3; color: #854d0e; }

.btn-pagar-restante {
  background: #ff6f00;
  color: white;
  border: none;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.btn-pagar-restante:hover:not(:disabled) { opacity: 0.85; }
.btn-pagar-restante:disabled { background: #d1d5db; cursor: not-allowed; }
</style>

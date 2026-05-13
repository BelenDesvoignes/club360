<template>
    <div class="p-8" style="padding-top: 100px; padding-left: 80px;">
    <h1 class="text-2xl font-bold mb-6" style="color: #0d124a">Mis Reservas</h1>
    
    <div v-if="loading" class="text-gray-500">Buscando tus Reservas...</div>
    
    <div v-else-if="reservations.length > 0" class="grid gap-4">
      <div v-for="res in reservations" :key="res.id" class="bg-white p-4 rounded-lg shadow border-l-4" style="border-color: #ff6f00">
        <div class="flex justify-between items-center">
          <div>
            <h3 class="font-bold text-lg">{{ res.activity_name }}</h3>
            <p class="text-gray-600">{{ res.court_name }}</p>
          </div>
          <div class="text-right">
            <p class="font-bold">{{ new Date(res.date).toLocaleDateString() }}</p>
            <p class="text-sm text-gray-500">{{ res.start_time }} hs</p>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="bg-blue-50 p-4 rounded text-blue-800">
      Parece que no tenés reservas todavía.
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../utils/api'; // El que creamos antes para FastAPI

const reservations = ref([]);
const loading = ref(false);

const fetchReservations = async () => {
  loading.value = true;
  try {
    // Usamos el ID 1 de prueba (para testear, editar luego ...): 
    const response = await api.get('/shifts/instances/user/1'); 
    reservations.value = response.data;
  } catch (e) {
    console.error("Error cargando turnos:", e);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchReservations);
</script>
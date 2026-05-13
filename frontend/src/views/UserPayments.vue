<template>
<div class="p-8" style="padding-top: 100px; padding-left: 80px;">
    <h1 class="text-2xl font-bold mb-6" style="color: #0d124a">Mis Pagos</h1>
    <div v-if="loading" class="text-gray-500">Cargando historial...</div>
    <div v-else class="bg-white rounded-lg shadow overflow-hidden">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr style="background-color: #0d124a; color: white">
            <th class="p-4">Fecha</th>
            <th class="p-4">Concepto</th>
            <th class="p-4">Monto</th>
            <th class="p-4">Estado</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in payments" :key="p.id" class="border-b hover:bg-gray-50">
            <td class="p-4">{{ new Date(p.date).toLocaleDateString() }}</td>
            <td class="p-4 capitalize">{{ p.type }}</td>
            <td class="p-4 font-bold">${{ p.amount }}</td>
            <td class="p-4 text-orange-600 font-semibold">{{ p.status }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../utils/api';

const payments = ref([]);
const loading = ref(false);

const fetchPayments = async () => {
  loading.value = true;
  try {
    const response = await api.get('/payments/user/1'); // ID de prueba () 
    payments.value = response.data;
  } catch (e) { console.error(e); }
  finally { loading.value = false; }
};

onMounted(fetchPayments);
</script>
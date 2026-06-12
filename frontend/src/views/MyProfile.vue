<template>
  <div class="profile-page">
    <section class="content-grid">
      <article class="panel">
        <div class="panel-header">
          <h3>Tu información</h3>
        </div>

        <div class="info-list" v-if="auth.user">
          <ProfileField 
            label="Nombre" 
            :value="auth.user.first_name" 
            field="first_name" 
            editable 
            @save="saveField" 
          />
          
          <ProfileField 
            label="Apellido" 
            :value="auth.user.last_name" 
            field="last_name" 
            editable 
            @save="saveField" 
          />
          
          <ProfileField 
            label="DNI" 
            :value="auth.user.dni" 
            :editable="false" 
          />
          
          <ProfileField 
            label="Correo electrónico" 
            :value="auth.user.email" 
            field="email" 
            editable 
            @save="saveField" 
          />
        </div>
        
        <div v-else class="loading-state">Cargando tus datos...</div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import ProfileField from '../components/ProfileField.vue' // ¡Extraje el componente para que sea más limpio!

const auth = useAuthStore()

const saveField = async (field, newValue) => {
  try {
    const payload = { ...auth.user, [field]: newValue }
    await auth.updateProfile(payload)
    await auth.refreshUser()
  } catch (e) {
    alert("Error al actualizar")
  }
}

onMounted(async () => {
  await auth.refreshUser()
})
</script>
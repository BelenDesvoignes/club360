<template>
  <div class="profile-row">
    <div class="row-header">
      <dt>{{ label }}</dt>
      <button v-if="editable && !isEditing" @click="isEditing = true" class="edit-icon-btn">✏️</button>
    </div>
    <dd>
      <div v-if="isEditing" class="edit-input-group">
        <input v-model="localValue" />
        <button @click="handleSave" class="save-btn">✔️</button>
        <button @click="isEditing = false" class="cancel-btn">❌</button>
      </div>
      <span v-else class="display-value">{{ value }}</span>
    </dd>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps(['label', 'value', 'field', 'editable'])
const emit = defineEmits(['save'])
const isEditing = ref(false)
const localValue = ref(props.value)

const handleSave = () => {
  emit('save', props.field, localValue.value)
  isEditing.value = false
}
</script>
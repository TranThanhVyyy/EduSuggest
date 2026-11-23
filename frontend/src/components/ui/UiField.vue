<script setup>
import { computed } from 'vue'

const props = defineProps({
  id: { type: String, required: true },
  label: { type: String, required: true },
  required: { type: Boolean, default: false },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
})

const hintId = computed(() => `${props.id}-hint`)
const errorId = computed(() => `${props.id}-error`)
const describedBy = computed(() => {
  if (props.error) return errorId.value
  if (props.hint) return hintId.value
  return undefined
})
</script>

<template>
  <div class="ui-field">
    <label class="ui-field__label" :for="id">
      {{ label }}<span v-if="required" class="ui-field__required"> *</span>
    </label>
    <slot :described-by="describedBy" />
    <span v-if="error" :id="errorId" class="ui-field__error" role="alert">{{ error }}</span>
    <span v-else-if="hint" :id="hintId" class="ui-field__hint">{{ hint }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tone: {
    type: String,
    default: 'neutral',
    validator: (value) => ['neutral', 'success', 'warning', 'danger', 'info'].includes(value),
  },
})

const badgeClass = computed(() => `ui-status-badge--${props.tone}`)
</script>

<template>
  <span class="ui-status-badge" :class="badgeClass">
    <slot />
  </span>
</template>

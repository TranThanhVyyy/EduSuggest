<script setup>
import { computed, ref } from 'vue'
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-vue-next'

const props = defineProps({
  variant: {
    type: String,
    default: 'info', // 'info' | 'success' | 'warning' | 'error' | 'danger'
    validator: (v) => ['info', 'success', 'warning', 'error', 'danger'].includes(v),
  },
  title: {
    type: String,
    default: '',
  },
  message: {
    type: String,
    default: '',
  },
  dismissible: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['dismiss'])
const visible = ref(true)

const normalizedVariant = computed(() => {
  return props.variant === 'error' ? 'danger' : props.variant
})

const variantConfig = computed(() => {
  const configs = {
    info: {
      icon: Info,
      classes: 'border-sky-200 bg-sky-50/80 text-sky-900',
      iconClass: 'text-sky-600',
    },
    success: {
      icon: CheckCircle2,
      classes: 'border-emerald-200 bg-emerald-50/80 text-emerald-900',
      iconClass: 'text-emerald-600',
    },
    warning: {
      icon: AlertTriangle,
      classes: 'border-amber-200 bg-amber-50/80 text-amber-900',
      iconClass: 'text-amber-600',
    },
    danger: {
      icon: AlertCircle,
      classes: 'border-rose-200 bg-rose-50/80 text-rose-900',
      iconClass: 'text-rose-600',
    },
  }
  return configs[normalizedVariant.value] || configs.info
})

function dismiss() {
  visible.value = false
  emit('dismiss')
}
</script>

<template>
  <div
    v-if="visible"
    role="alert"
    :class="[
      'flex items-start gap-3 rounded-lg border p-3.5 text-sm transition-all',
      variantConfig.classes,
    ]"
  >
    <component
      :is="variantConfig.icon"
      :size="18"
      :class="['shrink-0 mt-0.5', variantConfig.iconClass]"
      aria-hidden="true"
    />

    <div class="min-w-0 flex-1">
      <p v-if="title" class="font-bold leading-snug">
        {{ title }}
      </p>
      <div class="leading-relaxed" :class="title ? 'mt-0.5 text-xs opacity-95' : ''">
        <slot>{{ message }}</slot>
      </div>
    </div>

    <button
      v-if="dismissible"
      type="button"
      class="shrink-0 rounded p-1 opacity-70 hover:opacity-100 transition"
      aria-label="Đóng thông báo"
      @click="dismiss"
    >
      <X :size="15" aria-hidden="true" />
    </button>
  </div>
</template>

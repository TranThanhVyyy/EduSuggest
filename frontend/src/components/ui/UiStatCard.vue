<script setup>
import { computed } from 'vue'
import { TrendingDown, TrendingUp } from 'lucide-vue-next'

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  value: {
    type: [String, Number],
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
  icon: {
    type: Object,
    default: null,
  },
  trend: {
    type: Object,
    default: null, // { value: '+12%', isPositive: true }
  },
  variant: {
    type: String,
    default: 'default', // 'default' | 'primary' | 'teal' | 'amber' | 'surface'
    validator: (v) => ['default', 'primary', 'teal', 'amber', 'surface'].includes(v),
  },
  size: {
    type: String,
    default: 'md', // 'sm' | 'md' | 'lg'
    validator: (v) => ['sm', 'md', 'lg'].includes(v),
  },
})

const cardClasses = computed(() => {
  const base = 'bento-card relative flex flex-col justify-between overflow-hidden transition-all'
  const variants = {
    default: 'border-border bg-surface text-ink hover:border-slate-300',
    primary: 'border-navy bg-navy text-white shadow-md',
    teal: 'border-teal/30 bg-teal/5 text-ink hover:border-teal/50',
    amber: 'border-amber/30 bg-amber/5 text-ink hover:border-amber/50',
    surface: 'border-border bg-subtle text-ink',
  }
  const sizes = {
    sm: 'p-3.5 min-h-[96px]',
    md: 'p-5 min-h-[128px]',
    lg: 'p-6 min-h-[160px]',
  }
  return [base, variants[props.variant], sizes[props.size]]
})

const iconClasses = computed(() => {
  if (props.variant === 'primary') return 'bg-white/10 text-white'
  if (props.variant === 'teal') return 'bg-teal/15 text-teal'
  if (props.variant === 'amber') return 'bg-amber/15 text-amber'
  return 'bg-subtle text-navy'
})

const valueClasses = computed(() => {
  const sizes = {
    sm: 'text-xl font-bold tracking-tight',
    md: 'text-2xl sm:text-3xl font-bold tracking-tight',
    lg: 'text-3xl sm:text-4xl font-bold tracking-tight',
  }
  return sizes[props.size]
})
</script>

<template>
  <div :class="cardClasses">
    <div class="flex items-start justify-between gap-3">
      <p class="text-xs font-semibold uppercase tracking-wider text-muted truncate">
        {{ title }}
      </p>
      <div v-if="icon" :class="['flex shrink-0 items-center justify-center rounded-lg p-2', iconClasses]">
        <component :is="icon" :size="size === 'sm' ? 16 : 20" aria-hidden="true" />
      </div>
    </div>

    <div class="mt-2 flex items-baseline justify-between gap-2">
      <span :class="valueClasses" class="tabular-nums">
        {{ value }}
      </span>

      <div
        v-if="trend"
        class="inline-flex items-center gap-1 text-xs font-semibold tabular-nums"
        :class="trend.isPositive ? 'text-success' : 'text-danger'"
      >
        <TrendingUp v-if="trend.isPositive" :size="14" aria-hidden="true" />
        <TrendingDown v-else :size="14" aria-hidden="true" />
        <span>{{ trend.value }}</span>
      </div>
    </div>

    <p v-if="description" class="mt-2 text-xs leading-normal text-muted truncate">
      {{ description }}
    </p>
  </div>
</template>

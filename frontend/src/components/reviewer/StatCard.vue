<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], required: true },
  icon: { type: [Object, Function], required: true },
  tone: { type: String, default: 'primary' },
  detail: { type: String, default: '' },
})

const toneClasses = {
  primary: 'bg-primary/10 text-primary',
  accent: 'bg-accent/10 text-accent',
  navy: 'bg-navy/5 text-navy',
}
</script>

<template>
  <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex items-start justify-between gap-3">
      <p class="text-sm font-medium text-muted">{{ label }}</p>
      <span class="flex size-10 shrink-0 items-center justify-center rounded-xl" :class="toneClasses[tone] || toneClasses.primary">
        <component :is="icon" :size="19" aria-hidden="true" />
      </span>
    </div>
    <p class="mt-4 text-3xl font-bold tracking-tight text-navy">{{ value }}</p>
    <p v-if="detail" class="mt-1 text-xs text-muted">{{ detail }}</p>
  </article>
</template>

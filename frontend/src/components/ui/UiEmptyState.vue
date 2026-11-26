<script setup>
import { Inbox } from 'lucide-vue-next'

defineProps({
  title: {
    type: String,
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
  actionLabel: {
    type: String,
    default: '',
  },
  actionRoute: {
    type: [Object, String],
    default: null,
  },
})

const emit = defineEmits(['action'])

function handleAction() {
  emit('action')
}
</script>

<template>
  <div class="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-subtle/50 px-6 py-12 text-center">
    <div class="flex size-14 items-center justify-center rounded-2xl bg-surface border border-border text-muted shadow-sm">
      <component :is="icon || Inbox" :size="28" aria-hidden="true" />
    </div>

    <h3 class="mt-4 text-base font-bold text-navy">
      {{ title }}
    </h3>

    <p v-if="description" class="mt-1.5 max-w-md text-sm leading-relaxed text-muted">
      {{ description }}
    </p>

    <div v-if="actionLabel" class="mt-5">
      <RouterLink
        v-if="actionRoute"
        :to="actionRoute"
        class="ui-button ui-button--primary ui-button--sm"
      >
        {{ actionLabel }}
      </RouterLink>
      <button
        v-else
        type="button"
        class="ui-button ui-button--primary ui-button--sm"
        @click="handleAction"
      >
        {{ actionLabel }}
      </button>
    </div>
  </div>
</template>

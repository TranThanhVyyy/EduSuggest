<script setup>
import { reactive, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  mode: { type: String, default: 'view' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  record: { type: Object, default: null },
  fields: { type: Array, default: () => [] },
  confirmLabel: { type: String, default: 'Xác nhận' },
  saveLabel: { type: String, default: 'Lưu thay đổi' },
  error: { type: String, default: '' },
})

const emit = defineEmits(['close', 'save', 'confirm'])
const form = reactive({})
const localError = ref('')

function initializeForm() {
  for (const key of Object.keys(form)) delete form[key]
  for (const field of props.fields) {
    const value = props.record?.[field.key] ?? field.defaultValue ?? ''
    form[field.key] = Array.isArray(value) ? value.join('\n') : value
  }
}

watch(
  () => [props.open, props.record?.id, props.mode],
  ([isOpen]) => {
    if (isOpen) {
      localError.value = ''
      initializeForm()
    }
  },
  { immediate: true },
)

function submit() {
  const missingField = props.fields.find(
    (field) => field.required && !String(form[field.key] ?? '').trim(),
  )
  if (missingField) {
    localError.value = `Vui lòng nhập ${missingField.label.toLocaleLowerCase('vi')}.`
    return
  }

  const invalidEmailField = props.fields.find((field) =>
    field.type === 'email'
    && form[field.key]
    && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(form[field.key]).trim()),
  )
  if (invalidEmailField) {
    localError.value = `Vui lòng nhập ${invalidEmailField.label.toLocaleLowerCase('vi')} hợp lệ.`
    return
  }

  localError.value = ''
  emit('save', { ...form, ...(props.record?.id ? { id: props.record.id } : {}) })
}

function displayValue(value) {
  if (Array.isArray(value)) return value.join(', ')
  if (value === 'active') return 'Đang hoạt động'
  if (value === 'locked') return 'Đã khóa'
  if (value === 'visible') return 'Đang hiển thị'
  if (value === 'hidden') return 'Đã ẩn'
  return value || 'Chưa có dữ liệu'
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[60] flex items-end justify-center bg-navy/50 p-0 sm:items-center sm:p-4" @click.self="emit('close')" @keydown.esc="emit('close')">
    <section class="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6" role="dialog" aria-modal="true" aria-labelledby="admin-modal-title">
      <header class="flex items-start justify-between gap-4">
        <div>
          <h2 id="admin-modal-title" class="text-lg font-bold text-navy">{{ title }}</h2>
          <p v-if="description" class="mt-1 text-sm leading-6 text-muted">{{ description }}</p>
        </div>
        <button type="button" class="flex size-9 shrink-0 items-center justify-center rounded-lg text-muted hover:bg-background hover:text-navy" aria-label="Đóng hộp thoại" @click="emit('close')">
          <X :size="18" aria-hidden="true" />
        </button>
      </header>

      <div v-if="mode === 'confirm'" class="mt-5 rounded-xl border border-slate-200 bg-background p-4 text-sm leading-6 text-navy">
        <slot />
      </div>

      <dl v-else-if="mode === 'view'" class="mt-5 grid gap-x-5 gap-y-4 sm:grid-cols-2">
        <div v-for="field in fields" :key="field.key" class="min-w-0" :class="field.wide ? 'sm:col-span-2' : ''">
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">{{ field.label }}</dt>
          <dd class="mt-1 break-words whitespace-pre-line text-sm text-navy">{{ displayValue(record?.[field.key]) }}</dd>
        </div>
      </dl>

      <form v-else id="admin-modal-form" class="mt-5 space-y-4" novalidate @submit.prevent="submit">
        <div v-for="field in fields" :key="field.key">
          <label :for="`admin-field-${field.key}`" class="mb-1.5 block text-sm font-semibold text-navy">
            {{ field.label }}<span v-if="field.required" class="ml-1 text-primary" aria-hidden="true">*</span>
          </label>
          <select
            v-if="field.type === 'select'"
            :id="`admin-field-${field.key}`"
            v-model="form[field.key]"
            :required="field.required"
            :disabled="field.disabled"
            class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted"
          >
            <option v-if="field.placeholder" value="">{{ field.placeholder }}</option>
            <option v-for="option in field.options" :key="option.value ?? option" :value="option.value ?? option">
              {{ option.label ?? option }}
            </option>
          </select>
          <textarea
            v-else-if="field.type === 'textarea'"
            :id="`admin-field-${field.key}`"
            v-model="form[field.key]"
            :rows="field.rows || 3"
            :required="field.required"
            :disabled="field.disabled"
            :placeholder="field.placeholder"
            class="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted"
          ></textarea>
          <input
            v-else
            :id="`admin-field-${field.key}`"
            v-model="form[field.key]"
            :type="field.type || 'text'"
            :required="field.required"
            :disabled="field.disabled"
            :placeholder="field.placeholder"
            class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted"
          >
        </div>
      </form>

      <p v-if="error || localError" class="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ error || localError }}</p>
      <footer class="mt-6 flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 sm:flex-row sm:justify-end">
        <button type="button" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-navy hover:bg-background" @click="emit('close')">
          {{ mode === 'view' ? 'Đóng' : 'Hủy' }}
        </button>
        <button v-if="mode === 'confirm'" type="button" class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90" @click="emit('confirm')">
          {{ confirmLabel }}
        </button>
        <button v-else-if="mode === 'form'" type="submit" form="admin-modal-form" class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">
          {{ saveLabel }}
        </button>
      </footer>
    </section>
  </div>
</template>

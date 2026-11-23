<script setup>
import { computed, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  action: { type: String, default: '' },
  itemTitle: { type: String, default: '' },
  itemDescription: { type: String, default: '' },
  itemKind: { type: String, default: '' },
  saving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
})

const emit = defineEmits(['close', 'confirm'])
const note = ref('')
const error = ref('')

const actionContentByType = {
  approve: {
    title: 'Xác nhận phê duyệt',
    button: 'Phê duyệt nội dung',
    description: 'Quyết định sẽ được lưu vào hệ thống kiểm duyệt.',
    noteLabel: 'Ghi chú (không bắt buộc)',
    noteRequired: false,
  },
  reject: {
    title: 'Từ chối nội dung',
    button: 'Xác nhận từ chối',
    description: 'Hãy nêu rõ lý do để người tạo hiểu nội dung cần khắc phục.',
    noteLabel: 'Lý do từ chối',
    noteRequired: true,
  },
  requestChanges: {
    title: 'Yêu cầu chỉnh sửa',
    button: 'Gửi yêu cầu chỉnh sửa',
    description: 'Ghi cụ thể nội dung cần cập nhật trước khi gửi kiểm duyệt lại.',
    noteLabel: 'Nội dung yêu cầu',
    noteRequired: true,
  },
}

const actionContent = computed(() => actionContentByType[props.action] || {
  title: 'Xác nhận thao tác',
  button: 'Xác nhận',
  description: '',
  noteLabel: 'Ghi chú',
  noteRequired: true,
})

watch(
  () => [props.open, props.action],
  () => {
    note.value = ''
    error.value = ''
  },
)

function submit() {
  if (actionContent.value.noteRequired && !note.value.trim()) {
    error.value = 'Vui lòng nhập nội dung trước khi tiếp tục.'
    return
  }

  emit('confirm', { action: props.action, note: note.value.trim() })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 flex items-end justify-center bg-navy/50 p-0 sm:items-center sm:p-4" @click.self="emit('close')" @keydown.esc="emit('close')">
    <section class="w-full max-w-lg rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6" role="dialog" aria-modal="true" :aria-labelledby="'review-action-title'">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 id="review-action-title" class="text-lg font-bold text-navy">{{ actionContent.title }}</h2>
          <p class="mt-1 text-sm leading-6 text-muted">{{ actionContent.description }}</p>
        </div>
        <button type="button" class="flex size-9 shrink-0 items-center justify-center rounded-lg text-muted hover:bg-background hover:text-navy" aria-label="Đóng hộp thoại" @click="emit('close')">
          <X :size="18" aria-hidden="true" />
        </button>
      </div>

      <div class="mt-4 rounded-lg bg-background px-3 py-3">
        <p v-if="itemKind" class="text-xs font-medium uppercase tracking-wide text-muted">{{ itemKind }}</p>
        <p class="mt-1 break-words text-sm font-semibold text-navy">{{ itemTitle }}</p>
        <p v-if="itemDescription" class="mt-2 line-clamp-3 text-sm leading-6 text-muted">{{ itemDescription }}</p>
      </div>
      <form class="mt-4" novalidate @submit.prevent="submit">
        <label for="review-note" class="mb-1.5 block text-sm font-semibold text-navy">
          {{ actionContent.noteLabel }}
          <span v-if="actionContent.noteRequired" class="text-primary" aria-hidden="true">*</span>
        </label>
        <textarea
          id="review-note"
          v-model="note"
          rows="4"
          :required="actionContent.noteRequired"
          class="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none transition placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/15"
          :placeholder="actionContent.noteRequired ? 'Nhập nội dung chi tiết...' : 'Thêm ghi chú nếu cần...'"
          :aria-invalid="Boolean(error)"
          aria-describedby="review-note-error"
        ></textarea>
        <p v-if="error" id="review-note-error" class="mt-1 text-xs font-medium text-primary" role="alert">{{ error }}</p>
        <p v-if="errorMessage" class="mt-2 text-sm text-danger" role="alert">{{ errorMessage }}</p>
        <div class="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button type="button" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-navy transition hover:bg-background focus-visible:outline-2 focus-visible:outline-primary" @click="emit('close')">
            Hủy
          </button>
          <button type="submit" :disabled="saving" class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-wait disabled:opacity-60">
            {{ saving ? 'Đang lưu…' : actionContent.button }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>

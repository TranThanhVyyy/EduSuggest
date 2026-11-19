<script setup>
import { computed, reactive, ref } from 'vue'
import { Save, ShieldCheck } from 'lucide-vue-next'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import { getAdminProfile, saveAdminProfile } from '@/service/adminService'

const profile = computed(() => getAdminProfile())
const form = reactive({
  fullName: profile.value.fullName,
  email: profile.value.email,
  phone: profile.value.phone,
})
const formError = ref('')
const toastMessage = ref('')

function saveProfile() {
  formError.value = ''
  try {
    saveAdminProfile(form)
    toastMessage.value = 'Đã lưu hồ sơ mẫu trong phiên hiện tại.'
  } catch (error) {
    formError.value = error instanceof Error ? error.message : 'Không thể lưu hồ sơ.'
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-5">
    <section>
      <p class="text-sm text-muted">Tài khoản</p>
      <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Thông tin cá nhân</h2>
      <p class="mt-2 text-sm leading-6 text-muted">Cập nhật thông tin hồ sơ quản trị. Dữ liệu hiện chỉ lưu trong bộ nhớ của phiên.</p>
    </section>

    <form class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" novalidate @submit.prevent="saveProfile">
      <div class="mb-5 flex items-center gap-3 rounded-xl bg-background p-4">
        <span class="flex size-11 items-center justify-center rounded-full bg-primary/10 text-primary"><ShieldCheck :size="21" aria-hidden="true" /></span>
        <div>
          <p class="text-sm font-semibold text-navy">{{ profile.role }}</p>
          <p class="mt-0.5 text-xs text-muted">Quyền quản trị được bảo vệ</p>
        </div>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <label class="block">
          <span class="mb-1.5 block text-sm font-semibold text-navy">Họ tên <span class="text-primary" aria-hidden="true">*</span></span>
          <input v-model="form.fullName" type="text" autocomplete="name" required class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
        </label>
        <label class="block">
          <span class="mb-1.5 block text-sm font-semibold text-navy">Email <span class="text-primary" aria-hidden="true">*</span></span>
          <input v-model="form.email" type="email" autocomplete="email" required class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
        </label>
        <label class="block sm:col-span-2">
          <span class="mb-1.5 block text-sm font-semibold text-navy">Số điện thoại</span>
          <input v-model="form.phone" type="tel" autocomplete="tel" class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
        </label>
      </div>

      <p v-if="formError" class="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ formError }}</p>
      <div class="mt-5 flex justify-end border-t border-slate-100 pt-4">
        <button type="submit" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">
          <Save :size="16" aria-hidden="true" /> Lưu thay đổi
        </button>
      </div>
    </form>

    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>

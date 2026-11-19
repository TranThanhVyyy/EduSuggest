<script setup>
import { reactive, ref } from 'vue'
import { CalendarDays, Mail, Phone, Save, UserRound } from 'lucide-vue-next'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import { getReviewerProfile, saveReviewerProfile } from '@/service/reviewerService'

const profile = getReviewerProfile()
const form = reactive({
  fullName: profile.fullName,
  email: profile.email,
  phone: profile.phone,
})
const toastMessage = ref('')
const errorMessage = ref('')

function formatDate(value) {
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'long' }).format(new Date(value))
}

function saveProfile() {
  errorMessage.value = ''
  try {
    saveReviewerProfile(form)
    toastMessage.value = 'Thông tin hồ sơ đã được cập nhật trong phiên làm việc.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể cập nhật hồ sơ.'
  }
}
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-5">
    <section>
      <p class="text-sm text-muted">Cá nhân</p>
      <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Hồ sơ người kiểm duyệt</h2>
      <p class="mt-1 text-sm text-muted">Cập nhật thông tin liên hệ của bạn.</p>
    </section>

    <form class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" @submit.prevent="saveProfile">
      <div class="flex flex-col items-center gap-4 border-b border-slate-200 p-6 sm:flex-row sm:p-8">
        <span class="flex size-20 items-center justify-center rounded-full bg-primary/10 text-2xl font-bold text-primary">
          {{ form.fullName.split(' ').slice(-1)[0].slice(0, 1) }}
        </span>
        <div class="text-center sm:text-left">
          <h3 class="text-lg font-bold text-navy">{{ form.fullName }}</h3>
          <p class="mt-1 text-sm text-muted">{{ profile.role }}</p>
        </div>
      </div>

      <div class="grid gap-5 p-6 sm:grid-cols-2 sm:p-8">
        <label class="block">
          <span class="mb-1.5 block text-sm font-semibold text-navy">Họ và tên</span>
          <span class="relative block">
            <UserRound class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="17" aria-hidden="true" />
            <input v-model="form.fullName" required autocomplete="name" class="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          </span>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-sm font-semibold text-navy">Email</span>
          <span class="relative block">
            <Mail class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="17" aria-hidden="true" />
            <input v-model="form.email" type="email" required autocomplete="email" class="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          </span>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-sm font-semibold text-navy">Số điện thoại</span>
          <span class="relative block">
            <Phone class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="17" aria-hidden="true" />
            <input v-model="form.phone" type="tel" autocomplete="tel" class="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          </span>
        </label>

        <div>
          <span class="mb-1.5 block text-sm font-semibold text-navy">Vai trò</span>
          <div class="flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-background px-3 text-sm text-muted">
            <UserRound :size="16" aria-hidden="true" /> {{ profile.role }}
          </div>
        </div>

        <div class="sm:col-span-2">
          <span class="mb-1.5 block text-sm font-semibold text-navy">Ngày tham gia</span>
          <div class="flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-background px-3 text-sm text-muted">
            <CalendarDays :size="16" aria-hidden="true" /> {{ formatDate(profile.joinedAt) }}
          </div>
        </div>
      </div>

      <div class="flex flex-col-reverse items-start justify-between gap-3 border-t border-slate-200 px-6 py-4 sm:flex-row sm:items-center sm:px-8">
        <p v-if="errorMessage" class="text-sm font-medium text-primary" role="alert">{{ errorMessage }}</p>
        <p v-else class="text-xs text-muted">Thông tin được lưu tạm trong phiên trình duyệt.</p>
        <button type="submit" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
          <Save :size="16" aria-hidden="true" /> Lưu thay đổi
        </button>
      </div>
    </form>

    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, reactive, ref } from 'vue'
import { Camera, Save, UserPlus } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  getProviderApplication,
  getUserProfile,
  hasProviderRole,
  saveUserProfile,
} from '@/service/userService'

const profile = getUserProfile()
const form = reactive({ ...profile })
const application = getProviderApplication()
const errorMessage = ref('')
const toastMessage = ref('')
const generatedUrls = new Set()
const savedAvatar = ref(profile.avatarUrl)

function setAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    errorMessage.value = 'Chỉ chọn tệp hình ảnh.'
    return
  }
  const url = URL.createObjectURL(file)
  generatedUrls.add(url)
  form.avatarUrl = url
  errorMessage.value = ''
}

function save() {
  try {
    saveUserProfile(form)
    savedAvatar.value = form.avatarUrl
    errorMessage.value = ''
    toastMessage.value = 'Đã cập nhật hồ sơ minh họa trong phiên.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể cập nhật hồ sơ.'
  }
}

function applicationLabel(status) {
  return ({
    not_applied: 'Chưa đăng ký',
    pending: 'Đang chờ xét duyệt',
    approved: 'Đã được phê duyệt',
    rejected: 'Bị từ chối',
  })[status] || 'Chưa có dữ liệu'
}

onBeforeUnmount(() => {
  for (const url of generatedUrls) {
    if (url !== savedAvatar.value) URL.revokeObjectURL(url)
  }
})
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-5">
    <section><p class="text-sm text-muted">Tài khoản</p><h1 class="mt-1 text-2xl font-bold text-navy">Hồ sơ cá nhân</h1><p class="mt-2 text-sm text-muted">Thông tin minh họa. Email và ngày tham gia được Backend quản lý sau khi tích hợp.</p></section>
    <form class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" @submit.prevent="save">
      <div class="flex flex-wrap items-center gap-4 border-b border-slate-100 pb-5">
        <img v-if="form.avatarUrl" :src="form.avatarUrl" alt="Ảnh đại diện người học" class="size-16 rounded-full object-cover">
        <span v-else class="flex size-16 items-center justify-center rounded-full bg-primary/10 text-lg font-bold text-primary">{{ form.fullName.split(' ').slice(-1)[0]?.[0] || 'U' }}</span>
        <label class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-navy hover:bg-background"><Camera :size="16" aria-hidden="true" /> Cập nhật ảnh
          <input type="file" accept="image/*" class="sr-only" @change="setAvatar">
        </label>
        <span class="text-xs text-muted">Tệp chỉ tồn tại trong phiên demo.</span>
      </div>
      <div class="mt-5 grid gap-4 sm:grid-cols-2">
        <label class="text-sm font-semibold text-navy">Họ và tên *
          <input v-model="form.fullName" required class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
        </label>
        <label class="text-sm font-semibold text-navy">Email
          <input :value="profile.email" disabled class="mt-1.5 w-full rounded-xl border border-slate-200 bg-background px-3 py-2.5 text-sm text-muted">
        </label>
        <label class="text-sm font-semibold text-navy">Số điện thoại
          <input v-model="form.phone" type="tel" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
        </label>
        <label class="text-sm font-semibold text-navy">Ngày tham gia
          <input :value="profile.joinedAt" disabled class="mt-1.5 w-full rounded-xl border border-slate-200 bg-background px-3 py-2.5 text-sm text-muted">
        </label>
        <label class="text-sm font-semibold text-navy sm:col-span-2">Giới thiệu
          <textarea v-model="form.bio" rows="4" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"></textarea>
        </label>
      </div>
      <p v-if="errorMessage" class="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
      <button type="submit" class="mt-5 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90"><Save :size="15" aria-hidden="true" /> Lưu thay đổi</button>
    </form>

    <section class="rounded-2xl border border-accent/20 bg-accent/5 p-5 sm:p-6">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div><p class="text-xs font-semibold uppercase tracking-wide text-accent">Mở rộng vai trò</p><h2 class="mt-1 text-lg font-bold text-navy">{{ hasProviderRole() ? 'Bạn đã là nhà cung cấp' : 'Trở thành nhà cung cấp khóa học' }}</h2><p class="mt-2 max-w-2xl text-sm leading-6 text-muted">Chia sẻ kiến thức và xây dựng khóa học trên EduSuggest. Hồ sơ gửi đi không tạo tài khoản mới; Backend/Admin phải xét duyệt và cấp vai trò Provider.</p></div>
        <span class="rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-navy">{{ applicationLabel(application.status) }}</span>
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <RouterLink v-if="hasProviderRole()" :to="{ name: 'provider-dashboard' }" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white"><UserPlus :size="15" aria-hidden="true" /> Quản lý khóa học</RouterLink>
        <RouterLink v-else-if="application.status === 'pending'" :to="{ name: 'provider-application' }" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-navy"><UserPlus :size="15" aria-hidden="true" /> Xem hồ sơ đang chờ</RouterLink>
        <RouterLink v-else-if="application.status !== 'approved'" :to="{ name: 'provider-application' }" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90"><UserPlus :size="15" aria-hidden="true" /> {{ application.status === 'rejected' ? 'Chỉnh sửa và gửi lại' : 'Đăng ký trở thành nhà cung cấp' }}</RouterLink>
        <span v-else class="self-center text-sm font-semibold text-muted">Chờ Backend đồng bộ quyền Provider.</span>
        <p class="self-center text-xs text-muted">Quyền không được cấp bởi giao diện demo.</p>
      </div>
    </section>
    <p class="rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-muted">Đổi mật khẩu chưa khả dụng vì chưa có API xác thực. Không nhập hoặc lưu mật khẩu tại giao diện demo.</p>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>

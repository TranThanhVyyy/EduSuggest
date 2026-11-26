<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  KeyRound,
  Save,
  Send,
  ShieldCheck,
} from 'lucide-vue-next'
import UiButton from '@/components/ui/UiButton.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { authState, setSession } from '@/service/authState'
import { loadCurrentUser } from '@/service/authService'
import api from '@/service/api'

const specialties = ref([])
const profileData = ref(null)
const form = reactive({
  primarySpecialtyId: null,
  secondarySpecialtyIds: [],
  soNamKinhNghiem: null,
  tieuSu: '',
})

const pwdForm = reactive({
  matKhauHienTai: '',
  matKhauMoi: '',
  xacNhanMatKhau: '',
})
const pwdSaving = ref(false)
const pwdError = ref('')
const pwdSuccess = ref('')

const loading = ref(true)
const saving = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const user = computed(() => authState.user)
const mustChangePassword = computed(() => Boolean(user.value?.batBuocDoiMatKhau))

const groupedSpecialties = computed(() => {
  const groups = new Map()
  for (const item of specialties.value) {
    const key = item.nhomChuyenMon || 'Khác'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(item)
  }
  return Array.from(groups.entries()).map(([group, items]) => ({ group, items }))
})

const availableSecondaryGroups = computed(() =>
  groupedSpecialties.value
    .map(({ group, items }) => ({
      group,
      items: items.filter((item) => item.maChuyenMon !== form.primarySpecialtyId),
    }))
    .filter((entry) => entry.items.length > 0),
)

const verificationMeta = computed(() => {
  const status = profileData.value?.trangThaiHoSo || 'DRAFT'
  if (status === 'VERIFIED') {
    return {
      label: 'Đã xác minh · Đủ điều kiện kiểm duyệt',
      cls: 'border-teal/25 bg-teal/10 text-teal-dark',
      icon: ShieldCheck,
    }
  }
  if (status === 'PENDING_VERIFICATION') {
    return {
      label: 'Đang chờ Admin xác minh',
      cls: 'border-amber/25 bg-amber/10 text-amber',
      icon: Clock,
    }
  }
  if (status === 'NEEDS_UPDATE') {
    return {
      label: 'Cần bổ sung hồ sơ theo yêu cầu Admin',
      cls: 'border-danger/25 bg-danger/10 text-danger',
      icon: AlertTriangle,
    }
  }
  return {
    label: 'Bản nháp · Chưa gửi xác minh',
    cls: 'border-slate-200 bg-slate-100 text-slate-600',
    icon: CheckCircle2,
  }
})

function selectPrimary(specialtyId) {
  form.primarySpecialtyId = specialtyId
  form.secondarySpecialtyIds = form.secondarySpecialtyIds.filter((id) => id !== specialtyId)
}

function toggleSecondary(specialtyId) {
  if (specialtyId === form.primarySpecialtyId) return
  if (form.secondarySpecialtyIds.includes(specialtyId)) {
    form.secondarySpecialtyIds = form.secondarySpecialtyIds.filter((id) => id !== specialtyId)
  } else {
    form.secondarySpecialtyIds = [...form.secondarySpecialtyIds, specialtyId]
  }
}

function applyProfileResponse(data) {
  profileData.value = data
  form.primarySpecialtyId = data.primarySpecialty?.maChuyenMon ?? null
  form.secondarySpecialtyIds = (data.secondarySpecialties || []).map((s) => s.maChuyenMon)
  form.soNamKinhNghiem = data.soNamKinhNghiem ?? null
  form.tieuSu = data.tieuSu || ''
}

async function loadProfile() {
  if (mustChangePassword.value) {
    loading.value = false
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const [profileRes, specialtiesRes] = await Promise.all([
      api.get('/expert/profile'),
      api.get('/expert/specialties'),
    ])
    specialties.value = specialtiesRes.data || []
    applyProfileResponse(profileRes.data)
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải hồ sơ chuyên gia.'
  } finally {
    loading.value = false
  }
}

async function submitFirstPasswordChange() {
  pwdError.value = ''
  pwdSuccess.value = ''
  if (pwdForm.matKhauMoi.length < 8) {
    pwdError.value = 'Mật khẩu mới phải có ít nhất 8 ký tự.'
    return
  }
  if (pwdForm.matKhauMoi !== pwdForm.xacNhanMatKhau) {
    pwdError.value = 'Mật khẩu xác nhận không khớp.'
    return
  }
  pwdSaving.value = true
  try {
    const newPassword = pwdForm.matKhauMoi
    const username = user.value?.tenTaiKhoan
    await api.put('/users/change-password', {
      matKhauHienTai: pwdForm.matKhauHienTai,
      matKhauMoi: newPassword,
    })
    if (username) {
      const { data: loginData } = await api.post('/auth/login', {
        tenTaiKhoan: username,
        matKhau: newPassword,
      })
      setSession({
        accessToken: loginData.access_token,
        user: loginData.user,
      })
    } else {
      await loadCurrentUser()
    }
    pwdForm.matKhauHienTai = ''
    pwdForm.matKhauMoi = ''
    pwdForm.xacNhanMatKhau = ''
    pwdSuccess.value = 'Đổi mật khẩu thành công. Bạn đã có thể hoàn thiện hồ sơ chuyên môn.'
    await loadProfile()
  } catch (error) {
    pwdError.value = error.response?.data?.detail || 'Không thể đổi mật khẩu. Kiểm tra lại mật khẩu tạm thời.'
  } finally {
    pwdSaving.value = false
  }
}

async function persistDraft() {
  const uniqueSecondaries = Array.from(new Set(form.secondarySpecialtyIds)).filter(
    (id) => id !== form.primarySpecialtyId,
  )
  const years =
    form.soNamKinhNghiem === '' || form.soNamKinhNghiem === null
      ? null
      : Number(form.soNamKinhNghiem)
  const { data } = await api.put('/expert/profile', {
    primarySpecialtyId: form.primarySpecialtyId,
    secondarySpecialtyIds: uniqueSecondaries,
    soNamKinhNghiem: Number.isNaN(years) ? null : years,
    tieuSu: form.tieuSu.trim() || null,
  })
  applyProfileResponse(data)
  return data
}

async function saveDraft() {
  errorMessage.value = ''
  successMessage.value = ''
  saving.value = true
  try {
    await persistDraft()
    successMessage.value = 'Đã lưu nháp hồ sơ chuyên môn.'
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể lưu hồ sơ. Hãy thử lại.'
  } finally {
    saving.value = false
  }
}

async function submitForVerification() {
  errorMessage.value = ''
  successMessage.value = ''
  if (!form.primarySpecialtyId) {
    errorMessage.value = 'Vui lòng chọn đúng 1 chuyên môn chính trước khi gửi xác minh.'
    return
  }
  if (form.soNamKinhNghiem === '' || form.soNamKinhNghiem === null) {
    errorMessage.value = 'Vui lòng nhập số năm kinh nghiệm trước khi gửi xác minh.'
    return
  }
  if (!form.tieuSu.trim()) {
    errorMessage.value = 'Vui lòng mô tả kinh nghiệm kiểm duyệt trước khi gửi xác minh.'
    return
  }
  submitting.value = true
  try {
    await persistDraft()
    const { data } = await api.post('/expert/profile/submit')
    applyProfileResponse(data)
    successMessage.value = 'Đã gửi hồ sơ chuyên môn thành công. Vui lòng chờ Quản trị viên xác minh.'
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể gửi hồ sơ xác minh.'
  } finally {
    submitting.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <div class="max-w-4xl space-y-6">
    <!-- Mandatory First-Login Password Change Gate -->
    <section
      v-if="mustChangePassword"
      class="rounded-2xl border border-amber/35 bg-surface p-6 shadow-xs"
    >
      <div class="flex items-start gap-3">
        <span class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-amber/10 text-amber">
          <KeyRound :size="20" aria-hidden="true" />
        </span>
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.08em] text-amber">
            Bảo mật tài khoản · Lần đăng nhập đầu tiên
          </p>
          <h1 class="mt-1 font-display text-xl font-bold text-navy">
            Bắt buộc đổi mật khẩu trước khi tiếp tục
          </h1>
          <p class="mt-1 text-sm text-slate-600">
            Tài khoản chuyên gia của bạn đang sử dụng mật khẩu tạm thời do Quản trị viên cấp. Vui lòng đổi sang mật khẩu mới để mở khóa hồ sơ và chức năng kiểm duyệt.
          </p>
        </div>
      </div>

      <form class="mt-5 max-w-md space-y-4" @submit.prevent="submitFirstPasswordChange">
        <div>
          <label class="mb-1.5 block text-xs font-semibold text-navy">Mật khẩu tạm thời hiện tại</label>
          <input
            v-model="pwdForm.matKhauHienTai"
            type="password"
            class="ui-input"
            required
            autocomplete="current-password"
          >
        </div>
        <div>
          <label class="mb-1.5 block text-xs font-semibold text-navy">Mật khẩu mới (tối thiểu 8 ký tự)</label>
          <input
            v-model="pwdForm.matKhauMoi"
            type="password"
            class="ui-input"
            required
            minlength="8"
            autocomplete="new-password"
          >
        </div>
        <div>
          <label class="mb-1.5 block text-xs font-semibold text-navy">Xác nhận mật khẩu mới</label>
          <input
            v-model="pwdForm.xacNhanMatKhau"
            type="password"
            class="ui-input"
            required
            minlength="8"
            autocomplete="new-password"
          >
        </div>

        <p
          v-if="pwdError"
          class="rounded-xl border border-danger/25 bg-danger/5 px-3.5 py-2.5 text-xs font-medium text-danger"
          role="alert"
        >
          {{ pwdError }}
        </p>

        <UiButton type="submit" :loading="pwdSaving">
          <KeyRound :size="15" aria-hidden="true" />
          <span>Cập nhật mật khẩu &amp; Tiếp tục</span>
        </UiButton>
      </form>
    </section>

    <!-- Main Expert Specialty & Verification Form -->
    <template v-else>
      <section class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tài khoản chuyên gia
          </p>
          <h1 class="mt-1 font-display text-2xl font-bold tracking-tight text-navy">
            Hồ sơ &amp; Chuyên môn
          </h1>
          <p class="mt-1.5 text-sm text-slate-600">
            Chọn đúng 1 chuyên môn chính, các chuyên môn phụ và mô tả kinh nghiệm để gửi Quản trị viên xác minh.
          </p>
        </div>

        <span
          v-if="!loading"
          class="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold"
          :class="verificationMeta.cls"
        >
          <component :is="verificationMeta.icon" :size="14" aria-hidden="true" />
          <span>{{ verificationMeta.label }}</span>
        </span>
      </section>

      <p
        v-if="pwdSuccess"
        class="rounded-xl border border-teal/25 bg-teal/5 px-4 py-3 text-xs font-medium text-teal-dark"
      >
        {{ pwdSuccess }}
      </p>

      <!-- Admin Verification Feedback Banner -->
      <div
        v-if="!loading && profileData?.ghiChuXacMinh"
        class="rounded-2xl border px-4 py-3.5 text-xs leading-relaxed"
        :class="profileData.trangThaiHoSo === 'NEEDS_UPDATE'
          ? 'border-danger/30 bg-danger/5 text-danger'
          : 'border-teal/25 bg-teal/5 text-teal-dark'"
      >
        <p class="font-semibold">Phản hồi từ Quản trị viên:</p>
        <p class="mt-1">{{ profileData.ghiChuXacMinh }}</p>
      </div>

      <section class="rounded-2xl border border-border bg-surface p-6 shadow-xs">
        <div v-if="loading" class="space-y-4">
          <UiSkeleton variant="rect" height="64px" rounded="0.75rem" />
          <UiSkeleton variant="rect" height="240px" rounded="0.75rem" />
        </div>

        <form v-else class="space-y-6" @submit.prevent="saveDraft">
          <!-- Identity Summary -->
          <dl class="grid gap-4 rounded-xl bg-background/80 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt class="text-xs font-medium text-slate-500">Họ tên</dt>
              <dd class="mt-1 font-semibold text-navy">{{ user?.hoTen || '—' }}</dd>
            </div>
            <div>
              <dt class="text-xs font-medium text-slate-500">Email</dt>
              <dd class="mt-1 break-all font-semibold text-navy">{{ user?.email || '—' }}</dd>
            </div>
          </dl>

          <p
            v-if="profileData?.chuyenMon && !profileData?.primarySpecialty"
            class="rounded-xl border border-amber/25 bg-amber/5 px-4 py-3 text-xs leading-relaxed text-slate-700"
          >
            <strong class="font-semibold text-navy">Thông tin chuyên môn cũ:</strong> {{ profileData.chuyenMon }}.
            Hãy chọn chuyên môn chuẩn từ danh mục bên dưới và gửi hồ sơ xác minh.
          </p>

          <!-- 1. Primary Specialty (Grouped Radio) -->
          <fieldset class="space-y-4">
            <div>
              <legend class="text-sm font-bold text-navy">
                1. Chuyên môn chính <span class="text-danger">*</span>
              </legend>
              <p class="mt-0.5 text-xs text-slate-500">
                Chọn đúng 1 chuyên môn thế mạnh nhất của bạn. Hệ thống ưu tiên chuyên môn chính khi đề xuất phân công kiểm duyệt.
              </p>
            </div>

            <div v-for="grp in groupedSpecialties" :key="`p-grp-${grp.group}`" class="space-y-2">
              <p class="text-[11px] font-bold uppercase tracking-[0.07em] text-slate-400">
                {{ grp.group }}
              </p>
              <div class="grid gap-2.5 sm:grid-cols-2">
                <label
                  v-for="item in grp.items"
                  :key="`primary-${item.maChuyenMon}`"
                  class="flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors duration-150"
                  :class="form.primarySpecialtyId === item.maChuyenMon
                    ? 'border-teal bg-teal/[0.04] ring-1 ring-teal/30'
                    : 'border-border bg-surface hover:border-slate-300 hover:bg-background/60'"
                >
                  <input
                    type="radio"
                    name="primarySpecialty"
                    :value="item.maChuyenMon"
                    :checked="form.primarySpecialtyId === item.maChuyenMon"
                    class="mt-0.5 size-4 accent-teal"
                    @change="selectPrimary(item.maChuyenMon)"
                  >
                  <span class="min-w-0">
                    <span class="block text-sm font-semibold text-navy">{{ item.tenChuyenMon }}</span>
                    <span v-if="item.moTa" class="mt-0.5 block text-xs leading-relaxed text-slate-500">
                      {{ item.moTa }}
                    </span>
                  </span>
                </label>
              </div>
            </div>
          </fieldset>

          <!-- 2. Secondary Specialties (Grouped Checkboxes) -->
          <fieldset class="space-y-4 border-t border-border/70 pt-5">
            <div>
              <legend class="text-sm font-bold text-navy">
                2. Chuyên môn phụ (tùy chọn · chọn nhiều)
              </legend>
              <p class="mt-0.5 text-xs text-slate-500">
                Các chuyên môn liên quan bạn có thể hỗ trợ thẩm định. Chuyên môn chính được tự động loại trừ.
              </p>
            </div>

            <div v-for="grp in availableSecondaryGroups" :key="`s-grp-${grp.group}`" class="space-y-2">
              <p class="text-[11px] font-bold uppercase tracking-[0.07em] text-slate-400">
                {{ grp.group }}
              </p>
              <div class="grid gap-2 sm:grid-cols-2">
                <label
                  v-for="item in grp.items"
                  :key="`sec-${item.maChuyenMon}`"
                  class="flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors duration-150"
                  :class="form.secondarySpecialtyIds.includes(item.maChuyenMon)
                    ? 'border-navy/40 bg-subtle/80'
                    : 'border-border bg-surface hover:border-slate-300'"
                >
                  <input
                    type="checkbox"
                    :value="item.maChuyenMon"
                    :checked="form.secondarySpecialtyIds.includes(item.maChuyenMon)"
                    class="mt-0.5 size-4 rounded accent-navy"
                    @change="toggleSecondary(item.maChuyenMon)"
                  >
                  <span class="min-w-0">
                    <span class="block text-xs font-semibold text-navy">{{ item.tenChuyenMon }}</span>
                    <span v-if="item.moTa" class="mt-0.5 block line-clamp-2 text-[11px] text-slate-500">
                      {{ item.moTa }}
                    </span>
                  </span>
                </label>
              </div>
            </div>
          </fieldset>

          <!-- 3. Years of Experience & Bio -->
          <div class="grid gap-4 border-t border-border/70 pt-5 sm:grid-cols-3">
            <div>
              <label for="expert-years" class="mb-1.5 block text-sm font-bold text-navy">
                3. Số năm kinh nghiệm <span class="text-danger">*</span>
              </label>
              <input
                id="expert-years"
                v-model.number="form.soNamKinhNghiem"
                type="number"
                min="0"
                max="60"
                class="ui-input"
                placeholder="VD: 5"
              >
            </div>
            <div class="sm:col-span-2">
              <label for="expert-bio" class="mb-1.5 block text-sm font-bold text-navy">
                4. Mô tả kinh nghiệm &amp; học vị <span class="text-danger">*</span>
              </label>
              <textarea
                id="expert-bio"
                v-model="form.tieuSu"
                class="ui-input min-h-28 resize-y"
                rows="4"
                placeholder="Mô tả quá trình giảng dạy, dự án thực tế, chứng chỉ hoặc kinh nghiệm thẩm định học liệu..."
              />
            </div>
          </div>

          <p
            v-if="errorMessage"
            class="rounded-xl border border-danger/25 bg-danger/5 px-3.5 py-2.5 text-xs font-medium text-danger"
            role="alert"
          >
            {{ errorMessage }}
          </p>
          <p
            v-if="successMessage"
            class="rounded-xl border border-teal/25 bg-teal/5 px-3.5 py-2.5 text-xs font-medium text-teal-dark"
            role="status"
          >
            {{ successMessage }}
          </p>

          <div class="flex flex-wrap items-center justify-end gap-3 border-t border-border/70 pt-4">
            <UiButton
              type="submit"
              variant="outline"
              :loading="saving"
              :disabled="submitting"
            >
              <Save :size="15" aria-hidden="true" />
              <span>Lưu nháp</span>
            </UiButton>
            <UiButton
              type="button"
              variant="primary"
              :loading="submitting"
              :disabled="saving"
              @click="submitForVerification"
            >
              <Send :size="15" aria-hidden="true" />
              <span>Gửi hồ sơ xác minh</span>
            </UiButton>
          </div>
        </form>
      </section>
    </template>
  </div>
</template>

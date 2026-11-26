<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, RefreshCw } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { getPendingExpertCourses, getPendingExpertMaterials } from '@/service/expertApiService'

const props = defineProps({ kind: { type: String, required: true } })
const items = ref([])
const query = ref('')
const loading = ref(true)
const errorMessage = ref('')
const isForbidden = ref(false)
const isCourse = computed(() => props.kind === 'course')

const filteredItems = computed(() => {
  const q = query.value.trim().toLocaleLowerCase('vi')
  if (!q) return items.value
  return items.value.filter((item) =>
    `${item.id} ${item.title} ${item.category} ${item.provider}`.toLocaleLowerCase('vi').includes(q),
  )
})

async function loadItems() {
  loading.value = true
  errorMessage.value = ''
  isForbidden.value = false
  try {
    items.value = isCourse.value
      ? await getPendingExpertCourses()
      : await getPendingExpertMaterials()
  } catch (error) {
    isForbidden.value = error.response?.status === 403
    errorMessage.value = error.response?.data?.detail || 'Không thể tải danh sách. Hãy thử lại.'
  } finally {
    loading.value = false
  }
}

onMounted(loadItems)

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? '—'
    : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Editorial Header -->
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Hàng đợi kiểm duyệt</p>
        <h1 class="mt-1 font-display text-2xl font-bold tracking-tight text-navy">
          {{ isCourse ? 'Khóa học chờ duyệt' : 'Tài liệu chờ duyệt' }}
        </h1>
        <p class="mt-1.5 text-sm text-slate-600">
          {{ isCourse ? 'Rà soát đề cương, bài giảng và đưa ra kết luận thẩm định chuyên môn.' : 'Kiểm tra nội dung, liên kết học liệu và phê duyệt tài liệu độc lập.' }}
        </p>
      </div>

      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
        :disabled="loading"
        @click="loadItems"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
        <span>Làm mới</span>
      </button>
    </section>

    <!-- Unified Card Table -->
    <section class="overflow-hidden rounded-2xl border border-border bg-surface shadow-xs">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-border/80 px-5 py-3.5">
        <div class="w-full max-w-md">
          <SearchInput
            v-model="query"
            :label="isCourse ? 'Tìm khóa học chờ duyệt' : 'Tìm tài liệu chờ duyệt'"
            :placeholder="isCourse ? 'Tìm theo tên khóa học, mã...' : 'Tìm theo tên tài liệu, mã...'"
          />
        </div>
        <span class="text-xs font-medium text-slate-500 tabular-nums">
          {{ loading ? 'Đang tải…' : `${filteredItems.length} hồ sơ chờ duyệt` }}
        </span>
      </div>

      <div v-if="loading" class="space-y-3 p-5">
        <UiSkeleton v-for="i in 3" :key="i" variant="rect" height="56px" rounded="0.75rem" />
      </div>

      <div v-else-if="errorMessage" class="p-5">
        <div
          v-if="isForbidden"
          class="flex flex-col gap-3 rounded-xl border border-amber/30 bg-amber/[0.06] px-4 py-4 sm:flex-row sm:items-center sm:justify-between"
          role="status"
        >
          <div class="space-y-1">
            <p class="text-xs font-semibold uppercase tracking-[0.06em] text-amber">Chưa đủ điều kiện kiểm duyệt</p>
            <p class="text-sm text-navy">{{ errorMessage }}</p>
          </div>
          <RouterLink
            :to="{ name: 'reviewer-profile' }"
            class="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-teal px-3.5 text-xs font-semibold text-white hover:bg-teal-dark"
          >
            <span>Đi tới hồ sơ chuyên môn</span>
            <ArrowRight :size="13" aria-hidden="true" />
          </RouterLink>
        </div>
        <p v-else class="rounded-xl border border-danger/25 bg-danger/5 px-4 py-3 text-sm text-danger" role="alert">
          {{ errorMessage }}
          <button type="button" class="ml-2 font-semibold underline" @click="loadItems">Thử lại</button>
        </p>
      </div>

      <div v-else-if="filteredItems.length" class="overflow-x-auto">
        <table class="w-full min-w-[700px] text-left text-sm">
          <thead class="border-b border-border/80 bg-background text-[11px] uppercase tracking-[0.06em] text-slate-500">
            <tr>
              <th scope="col" class="whitespace-nowrap px-5 py-3 font-semibold">{{ isCourse ? 'Khóa học' : 'Tài liệu' }}</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 font-semibold">{{ isCourse ? 'Thông tin' : 'Định dạng' }}</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 font-semibold">Ngày gửi</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 font-semibold">Trạng thái</th>
              <th scope="col" class="whitespace-nowrap px-5 py-3 text-center font-semibold">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr
              v-for="item in filteredItems"
              :key="item.id"
              class="align-middle transition-colors duration-150 hover:bg-background/70"
            >
              <th scope="row" class="px-5 py-4 font-normal">
                <RouterLink
                  :to="{ name: isCourse ? 'reviewer-course-detail' : 'reviewer-material-detail', params: { id: item.id } }"
                  class="block break-words [overflow-wrap:anywhere] text-sm font-semibold text-navy hover:text-teal hover:underline"
                >
                  {{ item.title }}
                </RouterLink>
                <span class="mt-0.5 block text-xs text-slate-500 tabular-nums">
                  #{{ item.id }}<template v-if="item.provider"> · {{ item.provider }}</template>
                </span>
              </th>
              <td class="whitespace-nowrap px-4 py-4 text-xs text-slate-600">
                <template v-if="isCourse">
                  {{ item.category || 'Chưa phân loại' }}
                </template>
                <span v-else class="rounded border border-border bg-subtle px-2 py-0.5 text-xs font-bold uppercase text-navy">
                  {{ item.type || 'DOCUMENT' }}
                </span>
              </td>
              <td class="whitespace-nowrap px-4 py-4 text-xs text-slate-500 tabular-nums">
                {{ formatDate(item.submittedAt) }}
              </td>
              <td class="whitespace-nowrap px-4 py-4">
                <UiStatusBadge :status="item.status" />
              </td>
              <td class="whitespace-nowrap px-5 py-4 text-center">
                <RouterLink
                  :to="{ name: isCourse ? 'reviewer-course-detail' : 'reviewer-material-detail', params: { id: item.id } }"
                  class="inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-lg bg-teal px-3 text-xs font-semibold text-white shadow-[0_1px_2px_rgba(13,148,136,0.22)] transition-colors duration-150 hover:bg-teal-dark"
                >
                  <span>Thẩm định</span>
                  <ArrowRight :size="13" aria-hidden="true" />
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="p-6">
        <EmptyState
          :title="isCourse ? 'Không có khóa học chờ duyệt' : 'Không có tài liệu chờ duyệt'"
          :description="query ? 'Thử đổi từ khóa tìm kiếm.' : (isCourse ? 'Các khóa học mới gửi kiểm duyệt sẽ xuất hiện tại đây.' : 'Các tài liệu mới gửi kiểm duyệt sẽ xuất hiện tại đây.')"
        />
      </div>
    </section>
  </div>
</template>

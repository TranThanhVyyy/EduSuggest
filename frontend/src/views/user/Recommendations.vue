<script setup>
import { computed, onMounted, ref } from 'vue'
import { BookOpen, RefreshCw } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import CourseCard from '@/components/user/CourseCard.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchRecommendedCourses, fetchRecommendedMaterials } from '@/service/userApiService'

const route = useRoute()
const router = useRouter()
const isMaterialView = computed(() => route.name === 'material-recommendations')

const items = ref([])
const loading = ref(true)
const error = ref('')
const strategy = ref('none')
const personalized = ref(false)

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    if (isMaterialView.value) {
      const courseId = Number(route.query.course_id)
      const lessonId = route.query.lesson_id != null ? Number(route.query.lesson_id) : null
      if (!courseId || courseId <= 0) {
        error.value = 'Không thể tải gợi ý tài liệu: thiếu mã khóa học.'
        return
      }
      const result = await fetchRecommendedMaterials(courseId, { lessonId, limit: 12 })
      items.value = result
    } else {
      const result = await fetchRecommendedCourses({ limit: 12 })
      items.value = result.items
      strategy.value = result.strategy
      personalized.value = result.personalized
    }
  } catch (cause) {
    error.value = cause.response?.data?.detail || 'Không thể tải gợi ý. Hãy thử lại.'
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadData() })
</script>

<template>
  <div class="space-y-7">
    <header class="border-b border-border pb-5">
      <p class="ui-eyebrow">Học tập</p>
      <h1 class="ui-page-title mt-2">{{ isMaterialView ? 'Gợi ý tài liệu' : 'Gợi ý khóa học' }}</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-muted">
        {{ isMaterialView ? 'Tài liệu được đề xuất cho khóa học bạn đang học.' : 'Khóa học được gợi ý dựa trên lịch sử học tập và sở thích của bạn.' }}
      </p>
      <p v-if="!isMaterialView.value && strategy.value === 'latest'" class="mt-2 text-sm text-muted" role="status">
        Chưa có đủ lịch sử học tập để cá nhân hóa. Các khóa học dưới đây là gợi ý khám phá mới cập nhật.
      </p>
    </header>

    <p v-if="loading" class="py-6 text-sm text-muted" role="status">Đang tải gợi ý…</p>
    <section v-else-if="error" class="max-w-2xl border-l-2 border-danger py-1 pl-4" role="alert">
      <p class="text-sm text-danger">{{ error }}</p>
      <button class="mt-3 text-sm font-medium text-secondary underline" @click="loadData"><RefreshCw :size="14" aria-hidden="true" /> Thử lại</button>
    </section>
    <div v-else-if="items.length" class="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      <template v-if="isMaterialView">
        <MaterialCard v-for="item in items" :key="item.id" :material="item" />
      </template>
      <template v-else>
        <CourseCard v-for="item in items" :key="item.id" :course="item" />
      </template>
    </div>
    <section v-else class="max-w-2xl border-y border-border py-3">
      <EmptyState
        :title="isMaterialView ? 'Chưa có gợi ý tài liệu' : 'Chưa có gợi ý khóa học'"
        :description="isMaterialView ? 'Khóa học này chưa có tài liệu được đề xuất.' : 'Backend hiện chưa có khóa học phù hợp để gợi ý.'"
      />
      <RouterLink
        :to="{ name: isMaterialView ? 'material-catalog' : 'course-catalog' }"
        class="ml-5 inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline"
      >
        <BookOpen :size="16" aria-hidden="true" /> Xem danh mục {{ isMaterialView ? 'tài liệu' : 'khóa học' }}
      </RouterLink>
    </section>
  </div>
</template>

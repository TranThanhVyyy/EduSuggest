<script setup>
import { computed, ref } from 'vue'
import {
  ArrowUpRight,
  Bell,
  BookOpen,
  Bookmark,
  ChartNoAxesCombined,
  ChevronRight,
  Clock3,
  Compass,
  GraduationCap,
  LayoutDashboard,
  Search,
  SlidersHorizontal,
  Sparkles,
  Star,
  Users,
} from 'lucide-vue-next'

const activeView = ref('student')
const activeCategory = ref('Tất cả')
const searchQuery = ref('')

const categories = [
  { name: 'Tất cả', icon: Compass, count: '120+' },
  { name: 'Công nghệ', icon: BookOpen, count: '42 khóa học' },
  { name: 'Kinh doanh', icon: ChartNoAxesCombined, count: '28 khóa học' },
  { name: 'Thiết kế', icon: Sparkles, count: '19 khóa học' },
]

const courses = [
  {
    title: 'Vue.js 3 từ cơ bản đến thực chiến',
    provider: 'TechMaster Việt Nam',
    category: 'Công nghệ',
    rating: '4.9',
    duration: '18 giờ',
    level: 'Cơ bản',
    icon: BookOpen,
    iconClass: 'bg-primary/10 text-primary',
  },
  {
    title: 'Phân tích dữ liệu với Python',
    provider: 'FUNiX',
    category: 'Công nghệ',
    rating: '4.8',
    duration: '24 giờ',
    level: 'Trung cấp',
    icon: ChartNoAxesCombined,
    iconClass: 'bg-accent/10 text-accent',
  },
  {
    title: 'Tư duy thiết kế sản phẩm số',
    provider: 'Coursera',
    category: 'Thiết kế',
    rating: '4.9',
    duration: '12 giờ',
    level: 'Mọi cấp độ',
    icon: Sparkles,
    iconClass: 'bg-background text-navy',
  },
]

const visibleCourses = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase('vi')

  return courses.filter((course) => {
    const matchesCategory =
      activeCategory.value === 'Tất cả' || course.category === activeCategory.value
    const matchesSearch =
      !query ||
      `${course.title} ${course.provider} ${course.category}`.toLocaleLowerCase('vi').includes(query)

    return matchesCategory && matchesSearch
  })
})

const adminCourses = [
  { title: 'Vue.js 3 từ cơ bản đến thực chiến', category: 'Công nghệ', learners: '1.284', status: 'Đang hoạt động' },
  { title: 'Phân tích dữ liệu với Python', category: 'Công nghệ', learners: '986', status: 'Đang hoạt động' },
  { title: 'Tư duy thiết kế sản phẩm số', category: 'Thiết kế', learners: '742', status: 'Đang hoạt động' },
  { title: 'Quản trị dự án Agile', category: 'Kinh doanh', learners: '518', status: 'Chờ duyệt' },
]

const chartBars = [
  { day: 'T2', height: '42%' },
  { day: 'T3', height: '66%' },
  { day: 'T4', height: '52%' },
  { day: 'T5', height: '82%' },
  { day: 'T6', height: '62%' },
  { day: 'T7', height: '100%' },
  { day: 'CN', height: '76%' },
]
</script>

<template>
  <div v-if="activeView === 'student'" class="min-h-screen bg-background text-navy">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-6 px-4 py-4 sm:px-6 lg:px-8">
        <a href="#" class="flex shrink-0 items-center gap-2.5" aria-label="EduSuggest trang chủ">
          <span class="flex size-10 items-center justify-center rounded-xl bg-primary text-white">
            <GraduationCap :size="22" aria-hidden="true" />
          </span>
          <span class="text-xl font-bold tracking-tight">Edu<span class="text-primary">Suggest</span></span>
        </a>

        <nav class="hidden items-center gap-7 md:flex" aria-label="Điều hướng chính">
          <a href="#kham-pha" class="text-sm font-semibold text-primary">Khám phá</a>
          <a href="#khoa-hoc" class="text-sm font-medium text-muted transition hover:text-navy">Khóa học</a>
          <a href="#goi-y" class="text-sm font-medium text-muted transition hover:text-navy">Gợi ý cho bạn</a>
        </nav>

        <div class="flex items-center gap-2 sm:gap-3">
          <label class="relative hidden lg:block">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="17" aria-hidden="true" />
            <input
              v-model="searchQuery"
              type="search"
              placeholder="Tìm khóa học..."
              class="w-56 rounded-xl border border-slate-200 bg-background py-2.5 pl-10 pr-3 text-sm text-navy outline-none transition placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/15"
              aria-label="Tìm khóa học"
            >
          </label>
          <button
            type="button"
            class="hidden size-10 items-center justify-center rounded-xl text-muted transition hover:bg-background hover:text-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary sm:inline-flex"
            aria-label="Thông báo"
          >
            <Bell :size="19" aria-hidden="true" />
          </button>
          <button
            type="button"
            class="inline-flex whitespace-nowrap rounded-xl border border-slate-200 px-2 py-2 text-xs font-semibold text-navy transition hover:border-primary hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary sm:px-3 sm:text-sm"
            @click="activeView = 'admin'"
          >
            <span class="sm:hidden">Admin</span>
            <span class="hidden sm:inline">Bảng quản trị</span>
          </button>
          <button
            type="button"
            class="flex size-10 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            aria-label="Tài khoản học viên"
          >
            AN
          </button>
        </div>
      </div>
    </header>

    <main id="kham-pha" class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
      <section class="grid gap-5 lg:grid-cols-[1.55fr_1fr]">
        <div class="rounded-2xl bg-primary p-6 text-white sm:p-9">
          <span class="mb-5 inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold">
            <Sparkles :size="15" aria-hidden="true" />
            Lộ trình học dành riêng cho bạn
          </span>
          <h1 class="max-w-2xl text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
            Học đúng điều bạn cần, tiến xa hơn mỗi ngày.
          </h1>
          <p class="mt-4 max-w-xl text-sm leading-6 text-white/85 sm:text-base">
            Khám phá khóa học phù hợp với mục tiêu và xây dựng lộ trình phát triển của riêng bạn.
          </p>
          <a
            href="#goi-y"
            class="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-bold text-primary transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            Xem gợi ý học tập
            <ArrowUpRight :size="17" aria-hidden="true" />
          </a>
        </div>

        <div class="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
          <div>
            <div class="flex size-11 items-center justify-center rounded-xl bg-accent/10 text-accent">
              <Sparkles :size="21" aria-hidden="true" />
            </div>
            <p class="mt-5 text-sm font-semibold text-accent">Gợi ý thông minh</p>
            <h2 class="mt-2 text-xl font-bold leading-snug text-navy">
              Bắt đầu từ mục tiêu bạn muốn chinh phục
            </h2>
            <p class="mt-2 text-sm leading-6 text-muted">
              Hệ thống gợi ý nội dung học tập phù hợp với định hướng nghề nghiệp của bạn.
            </p>
          </div>
          <a href="#goi-y" class="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">
            Khám phá lộ trình <ChevronRight :size="17" aria-hidden="true" />
          </a>
        </div>
      </section>

      <section class="mt-10" aria-labelledby="category-title">
        <div class="flex items-end justify-between gap-4">
          <div>
            <p class="text-sm font-medium text-muted">Bắt đầu từ lĩnh vực bạn yêu thích</p>
            <h2 id="category-title" class="mt-1 text-xl font-bold tracking-tight text-navy">Danh mục nổi bật</h2>
          </div>
          <button type="button" class="hidden text-sm font-semibold text-primary hover:underline sm:inline-flex">
            Tất cả danh mục <ChevronRight :size="16" aria-hidden="true" />
          </button>
        </div>
        <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <button
            v-for="category in categories"
            :key="category.name"
            type="button"
            class="rounded-xl border p-4 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            :class="activeCategory === category.name ? 'border-primary bg-primary/5' : 'border-slate-200 bg-white hover:border-primary/40'"
            :aria-pressed="activeCategory === category.name"
            @click="activeCategory = category.name"
          >
            <component
              :is="category.icon"
              class="mb-4 text-primary"
              :size="20"
              aria-hidden="true"
            />
            <span class="block text-sm font-bold text-navy">{{ category.name }}</span>
            <span class="mt-1 block text-xs text-muted">{{ category.count }}</span>
          </button>
        </div>
      </section>

      <section id="khoa-hoc" class="mt-10" aria-labelledby="courses-title">
        <div class="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p class="text-sm font-medium text-muted">Được chọn lọc dành cho bạn</p>
            <h2 id="courses-title" class="mt-1 text-xl font-bold tracking-tight text-navy">Khóa học đề xuất</h2>
          </div>
          <div class="flex w-full gap-2 lg:hidden">
            <label class="relative min-w-0 flex-1">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="17" aria-hidden="true" />
              <input
                v-model="searchQuery"
                type="search"
                placeholder="Tìm khóa học..."
                class="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm outline-none transition placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/15"
                aria-label="Tìm khóa học"
              >
            </label>
            <button type="button" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-navy">
              <SlidersHorizontal :size="16" aria-hidden="true" />
              Lọc
            </button>
          </div>
          <button type="button" class="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-navy transition hover:border-primary hover:text-primary sm:inline-flex">
            <SlidersHorizontal :size="16" aria-hidden="true" />
            Lọc khóa học
          </button>
        </div>

        <div v-if="visibleCourses.length" class="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <article v-for="course in visibleCourses" :key="course.title" class="rounded-2xl border border-slate-200 bg-white p-5 transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md">
            <div class="flex items-start justify-between">
              <div class="flex size-12 items-center justify-center rounded-xl" :class="course.iconClass">
                <component :is="course.icon" :size="22" aria-hidden="true" />
              </div>
              <button type="button" class="rounded-lg p-2 text-muted transition hover:bg-background hover:text-primary focus-visible:outline-2 focus-visible:outline-primary" :aria-label="`Lưu khóa học ${course.title}`">
                <Bookmark :size="18" aria-hidden="true" />
              </button>
            </div>
            <div class="mt-5 flex items-center gap-2">
              <span class="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">{{ course.category }}</span>
              <span class="rounded-full bg-background px-2.5 py-1 text-xs font-medium text-muted">{{ course.level }}</span>
            </div>
            <h3 class="mt-3 min-h-12 text-base font-bold leading-6 text-navy">{{ course.title }}</h3>
            <p class="mt-1 text-sm text-muted">{{ course.provider }}</p>
            <div class="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-xs text-muted">
              <span class="inline-flex items-center gap-1 font-semibold text-navy"><Star :size="15" class="fill-primary text-primary" aria-hidden="true" /> {{ course.rating }}</span>
              <span class="inline-flex items-center gap-1"><Clock3 :size="15" aria-hidden="true" /> {{ course.duration }}</span>
              <button type="button" class="font-semibold text-primary hover:underline">Chi tiết</button>
            </div>
          </article>
        </div>
        <p v-else class="mt-4 rounded-xl border border-slate-200 bg-white p-6 text-center text-sm text-muted">
          Chưa tìm thấy khóa học phù hợp. Hãy thử từ khóa hoặc danh mục khác.
        </p>
      </section>

      <section id="goi-y" class="mt-10 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7" aria-labelledby="recommendation-title">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-start gap-3">
            <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-accent/10 text-accent">
              <Sparkles :size="21" aria-hidden="true" />
            </span>
            <div>
              <p class="text-sm font-semibold text-accent">EduSuggest AI</p>
              <h2 id="recommendation-title" class="mt-1 text-lg font-bold text-navy">Gợi ý tiếp theo cho bạn</h2>
              <p class="mt-1 text-sm text-muted">Dựa trên lĩnh vực Công nghệ và mục tiêu phát triển kỹ năng.</p>
            </div>
          </div>
          <button type="button" class="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">
            Xem lộ trình <ChevronRight :size="16" aria-hidden="true" />
          </button>
        </div>
      </section>
    </main>

    <footer class="border-t border-slate-200 bg-white">
      <div class="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-5 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <p><span class="font-bold text-navy">EduSuggest</span> · Học đúng hướng, vững tương lai.</p>
        <p>© 2026 EduSuggest. Đồng hành cùng hành trình học tập của bạn.</p>
      </div>
    </footer>
  </div>

  <div v-else class="min-h-screen bg-background text-navy lg:grid lg:grid-cols-[248px_minmax(0,1fr)]">
    <aside class="hidden min-h-screen flex-col bg-navy px-4 py-6 text-white lg:flex">
      <a href="#" class="flex items-center gap-2.5 px-2" aria-label="EduSuggest quản trị">
        <span class="flex size-10 items-center justify-center rounded-xl bg-primary text-white">
          <GraduationCap :size="22" aria-hidden="true" />
        </span>
        <span class="text-lg font-bold">EduSuggest</span>
      </a>
      <p class="mb-3 mt-10 px-3 text-xs font-semibold uppercase tracking-wider text-white/50">Quản lý</p>
      <nav class="space-y-1" aria-label="Điều hướng quản trị">
        <a href="#" class="flex items-center gap-3 rounded-xl bg-primary px-3 py-2.5 text-sm font-semibold text-white">
          <LayoutDashboard :size="18" aria-hidden="true" /> Tổng quan
        </a>
        <a href="#" class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white/75 transition hover:bg-white/10 hover:text-white">
          <BookOpen :size="18" aria-hidden="true" /> Khóa học
        </a>
        <a href="#" class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white/75 transition hover:bg-white/10 hover:text-white">
          <Users :size="18" aria-hidden="true" /> Học viên
        </a>
        <a href="#" class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white/75 transition hover:bg-white/10 hover:text-white">
          <Sparkles :size="18" aria-hidden="true" /> Gợi ý AI
        </a>
      </nav>
      <div class="mt-auto rounded-xl border border-white/10 bg-white/5 p-4">
        <p class="text-sm font-semibold">Cần hỗ trợ?</p>
        <p class="mt-1 text-xs leading-5 text-white/60">Xem hướng dẫn quản lý EduSuggest.</p>
        <button type="button" class="mt-3 text-xs font-semibold text-white underline underline-offset-4">Trung tâm trợ giúp</button>
      </div>
    </aside>

    <div class="min-w-0">
      <header class="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-4 sm:px-7">
        <div>
          <p class="text-sm text-muted">EduSuggest / Quản trị</p>
          <h1 class="mt-1 text-xl font-bold tracking-tight text-navy">Tổng quan</h1>
        </div>
        <div class="flex items-center gap-2 sm:gap-4">
          <label class="relative hidden md:block">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="17" aria-hidden="true" />
            <input type="search" placeholder="Tìm kiếm..." class="w-52 rounded-xl border border-slate-200 bg-background py-2.5 pl-10 pr-3 text-sm outline-none transition placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/15">
          </label>
          <button type="button" class="hidden size-10 items-center justify-center rounded-xl text-muted hover:bg-background focus-visible:outline-2 focus-visible:outline-primary sm:inline-flex" aria-label="Thông báo">
            <Bell :size="19" aria-hidden="true" />
          </button>
          <span class="flex size-10 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary" aria-label="Quản trị viên">AD</span>
          <button type="button" class="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-navy transition hover:border-primary hover:text-primary focus-visible:outline-2 focus-visible:outline-primary" @click="activeView = 'student'">
            <span class="sm:hidden">Học viên</span>
            <span class="hidden sm:inline">Giao diện học viên</span>
          </button>
        </div>
      </header>

      <nav class="flex gap-2 overflow-x-auto border-b border-slate-200 bg-white px-4 py-3 lg:hidden" aria-label="Điều hướng quản trị">
        <a href="#" class="inline-flex shrink-0 items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"><LayoutDashboard :size="16" aria-hidden="true" /> Tổng quan</a>
        <a href="#" class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted hover:bg-background hover:text-navy"><BookOpen :size="16" aria-hidden="true" /> Khóa học</a>
        <a href="#" class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted hover:bg-background hover:text-navy"><Users :size="16" aria-hidden="true" /> Học viên</a>
        <a href="#" class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted hover:bg-background hover:text-navy"><Sparkles :size="16" aria-hidden="true" /> Gợi ý AI</a>
      </nav>

      <main class="mx-auto max-w-7xl space-y-6 p-4 sm:p-7">
        <section class="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 class="text-2xl font-bold tracking-tight text-navy">Chào buổi sáng, Admin</h2>
            <p class="mt-1 text-sm text-muted">Đây là tình hình hoạt động của hệ thống hôm nay.</p>
            <p class="mt-1 text-xs text-muted">Bản xem trước giao diện · Dữ liệu minh họa</p>
          </div>
          <button type="button" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50">
            <BookOpen :size="17" aria-hidden="true" /> Thêm khóa học
          </button>
        </section>

        <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Chỉ số tổng quan">
          <article class="rounded-2xl border border-slate-200 bg-white p-5">
            <p class="text-sm font-medium text-muted">Tổng khóa học</p>
            <div class="mt-3 flex items-end justify-between">
              <p class="text-3xl font-bold tracking-tight text-navy">248</p>
              <span class="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">+12 tháng này</span>
            </div>
          </article>
          <article class="rounded-2xl border border-slate-200 bg-white p-5">
            <p class="text-sm font-medium text-muted">Học viên</p>
            <div class="mt-3 flex items-end justify-between">
              <p class="text-3xl font-bold tracking-tight text-navy">8.426</p>
              <span class="rounded-full bg-accent/10 px-2.5 py-1 text-xs font-semibold text-accent">+8,4%</span>
            </div>
          </article>
          <article class="rounded-2xl border border-slate-200 bg-white p-5">
            <p class="text-sm font-medium text-muted">Lượt ghi danh</p>
            <div class="mt-3 flex items-end justify-between">
              <p class="text-3xl font-bold tracking-tight text-navy">1.294</p>
              <span class="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">+5,2%</span>
            </div>
          </article>
          <article class="rounded-2xl border border-slate-200 bg-white p-5">
            <p class="text-sm font-medium text-muted">Gợi ý AI</p>
            <div class="mt-3 flex items-end justify-between">
              <p class="text-3xl font-bold tracking-tight text-navy">3.672</p>
              <span class="flex size-9 items-center justify-center rounded-xl bg-accent/10 text-accent"><Sparkles :size="18" aria-hidden="true" /></span>
            </div>
          </article>
        </section>

        <section class="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
          <article class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <div class="flex items-start justify-between gap-3">
              <div>
                <h2 class="font-bold text-navy">Hoạt động học tập</h2>
                <p class="mt-1 text-sm text-muted">Lượt ghi danh trong tuần này</p>
              </div>
              <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-muted hover:text-navy">7 ngày qua</button>
            </div>
            <div class="mt-7 flex h-44 items-end justify-between gap-3 border-b border-slate-200 px-2">
              <div v-for="(bar, index) in chartBars" :key="bar.day" class="flex h-full flex-1 flex-col items-center justify-end gap-2">
                <div class="flex w-full items-end justify-center" :style="{ height: bar.height }">
                  <div class="w-full max-w-10 rounded-t-md" :class="index === 5 ? 'bg-primary' : 'bg-primary/20'" style="height: 100%"></div>
                </div>
                <span class="pb-2 text-xs text-muted">{{ bar.day }}</span>
              </div>
            </div>
          </article>

          <article class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="font-bold text-navy">Gợi ý AI</h2>
                <p class="mt-1 text-sm text-muted">Tương tác trong 7 ngày qua</p>
              </div>
              <span class="flex size-10 items-center justify-center rounded-xl bg-accent/10 text-accent"><Sparkles :size="20" aria-hidden="true" /></span>
            </div>
            <p class="mt-7 text-4xl font-bold tracking-tight text-navy">3.672</p>
            <p class="mt-1 text-sm text-muted">lượt gợi ý được tạo</p>
            <div class="mt-6 h-2 overflow-hidden rounded-full bg-background">
              <div class="h-full w-3/4 rounded-full bg-accent"></div>
            </div>
            <p class="mt-3 text-xs text-muted">Mức độ sử dụng ổn định trong tuần này</p>
          </article>
        </section>

        <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5">
            <div>
              <h2 class="font-bold text-navy">Khóa học gần đây</h2>
              <p class="mt-1 text-sm text-muted">Theo dõi trạng thái và số lượng học viên</p>
            </div>
            <button type="button" class="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">
              Xem tất cả <ArrowUpRight :size="16" aria-hidden="true" />
            </button>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[640px] text-left text-sm">
              <thead class="bg-background text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th scope="col" class="px-5 py-3 font-semibold">Tên khóa học</th>
                  <th scope="col" class="px-5 py-3 font-semibold">Danh mục</th>
                  <th scope="col" class="px-5 py-3 font-semibold">Học viên</th>
                  <th scope="col" class="px-5 py-3 font-semibold">Trạng thái</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="course in adminCourses" :key="course.title" class="transition hover:bg-background/70">
                  <th scope="row" class="px-5 py-4 font-semibold text-navy">{{ course.title }}</th>
                  <td class="px-5 py-4 text-muted">{{ course.category }}</td>
                  <td class="px-5 py-4 text-muted">{{ course.learners }}</td>
                  <td class="px-5 py-4">
                    <span class="rounded-full px-2.5 py-1 text-xs font-semibold" :class="course.status === 'Đang hoạt động' ? 'bg-accent/10 text-accent' : 'bg-primary/10 text-primary'">
                      {{ course.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

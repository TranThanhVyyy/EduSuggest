<script setup>
import { computed, ref, watch } from 'vue'
import { Download, ExternalLink, FileText, LoaderCircle, X, ZoomIn } from 'lucide-vue-next'

const props = defineProps({
  resource: { type: [Object, String], default: null },
})

const isLoading = ref(false)
const hasLoadError = ref(false)
const isZoomed = ref(false)

const normalizedResource = computed(() => {
  if (typeof props.resource === 'string') {
    return { type: 'text', text: props.resource }
  }

  return props.resource
})

const resourceName = computed(() =>
  normalizedResource.value?.fileName
  || normalizedResource.value?.name
  || normalizedResource.value?.title
  || 'Tài liệu',
)

const rawUrl = computed(() =>
  normalizedResource.value?.url
  || normalizedResource.value?.fileUrl
  || normalizedResource.value?.src
  || '',
)

function resolveSafeUrl(value, allowBlob = true) {
  if (typeof value !== 'string' || !value.trim()) return ''

  try {
    const baseUrl = typeof window === 'undefined' ? 'http://localhost' : window.location.origin
    const url = new URL(value.trim(), baseUrl)
    const allowedProtocols = allowBlob ? ['http:', 'https:', 'blob:'] : ['http:', 'https:']

    if (!allowedProtocols.includes(url.protocol) || url.username || url.password) return ''
    return url.href
  } catch {
    return ''
  }
}

const sourceUrl = computed(() => resolveSafeUrl(rawUrl.value))
const isExternalLink = computed(() =>
  ['link', 'url'].includes(String(normalizedResource.value?.type || normalizedResource.value?.kind || '').toLowerCase()),
)
const linkUrl = computed(() => resolveSafeUrl(rawUrl.value, false))

const textContent = computed(() => {
  const resource = normalizedResource.value
  if (!resource || typeof resource !== 'object') return ''

  for (const key of ['text', 'textContent', 'contentText']) {
    if (typeof resource[key] === 'string' && resource[key].trim()) return resource[key]
  }

  if (typeof resource.content === 'string' && resource.content.trim()) return resource.content
  if (typeof resource.body === 'string' && resource.body.trim()) return resource.body
  return ''
})

const previewKind = computed(() => {
  const resource = normalizedResource.value
  if (!resource || typeof resource !== 'object') return 'text'

  const declaredType = String(resource.type || resource.kind || '').toLowerCase()
  if (isExternalLink.value) return 'link'
  if (['image', 'video', 'pdf', 'text'].includes(declaredType)) return declaredType
  if (textContent.value) return 'text'

  const mimeType = String(resource.mimeType || resource.contentType || '').toLowerCase()
  const fileLabel = String(resource.fileName || resource.name || rawUrl.value).split(/[?#]/)[0]
  const extension = fileLabel.split('.').pop()?.toLowerCase() || ''

  if (mimeType.startsWith('image/') || ['avif', 'gif', 'jpeg', 'jpg', 'png', 'svg', 'webp'].includes(extension)) return 'image'
  if (mimeType.startsWith('video/') || ['m4v', 'mov', 'mp4', 'webm'].includes(extension)) return 'video'
  if (mimeType === 'application/pdf' || extension === 'pdf') return 'pdf'
  if (['doc', 'docx', 'odp', 'ods', 'odt', 'ppt', 'pptx', 'xls', 'xlsx'].includes(extension)) return 'office'
  return 'unsupported'
})

watch(
  [sourceUrl, previewKind],
  ([url, kind]) => {
    hasLoadError.value = false
    isZoomed.value = false
    isLoading.value = Boolean(url && ['image', 'pdf', 'video'].includes(kind))
  },
  { immediate: true },
)

function handleLoad() {
  isLoading.value = false
  hasLoadError.value = false
}

function handleError() {
  isLoading.value = false
  hasLoadError.value = true
}
</script>

<template>
  <section class="min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white" aria-label="Xem trước nội dung">
    <div v-if="!normalizedResource" class="p-5 text-sm text-muted" role="status">
      Chưa có dữ liệu nội dung để xem trước.
    </div>

    <template v-else-if="previewKind === 'text'">
      <pre v-if="textContent" class="max-h-[34rem] overflow-auto whitespace-pre-wrap break-words p-4 text-sm leading-7 text-navy">{{ textContent }}</pre>
      <div v-else class="p-5 text-sm text-muted" role="status">Chưa có nội dung văn bản để xem trước.</div>
    </template>

    <template v-else-if="previewKind === 'link'">
      <div v-if="linkUrl" class="flex flex-wrap items-center justify-between gap-3 p-4">
        <a :href="linkUrl" target="_blank" rel="noopener noreferrer" class="inline-flex min-w-0 items-center gap-2 break-all text-sm font-semibold text-primary underline">
          <ExternalLink class="shrink-0" :size="16" aria-hidden="true" /> {{ rawUrl }}
        </a>
        <span class="text-xs text-muted">Liên kết sẽ mở trong tab mới.</span>
      </div>
      <div v-else class="p-5 text-sm text-muted" role="alert">Liên kết không tồn tại hoặc không an toàn nên không thể mở.</div>
    </template>

    <div v-else-if="previewKind === 'image' && sourceUrl" class="relative flex min-h-40 items-center justify-center bg-slate-50 p-3">
      <p v-if="isLoading" class="absolute z-10 inline-flex items-center gap-2 rounded-lg bg-white/95 px-3 py-2 text-sm text-muted shadow-sm" role="status">
        <LoaderCircle class="animate-spin" :size="16" aria-hidden="true" /> Đang tải ảnh...
      </p>
      <div v-if="hasLoadError" class="max-w-md p-4 text-center">
        <p class="text-sm text-muted" role="alert">Không thể tải ảnh xem trước.</p>
        <div class="mt-3 flex flex-wrap justify-center gap-2">
          <a :href="sourceUrl" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-navy hover:border-primary hover:text-primary">
            <ExternalLink :size="15" aria-hidden="true" /> Mở tệp
          </a>
          <a :href="sourceUrl" :download="resourceName" class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:opacity-90">
            <Download :size="15" aria-hidden="true" /> Tải xuống
          </a>
        </div>
      </div>
      <template v-else>
        <img :src="sourceUrl" :alt="resourceName" class="max-h-[34rem] max-w-full object-contain" @load="handleLoad" @error="handleError" />
        <button type="button" class="absolute bottom-4 right-4 inline-flex items-center gap-2 rounded-lg bg-navy/85 px-3 py-2 text-xs font-semibold text-white hover:bg-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary" @click="isZoomed = true">
          <ZoomIn :size="15" aria-hidden="true" /> Phóng to
        </button>
      </template>
    </div>

    <div v-else-if="previewKind === 'video' && sourceUrl" class="relative bg-navy">
      <p v-if="isLoading" class="absolute left-1/2 top-1/2 z-10 inline-flex -translate-x-1/2 -translate-y-1/2 items-center gap-2 rounded-lg bg-white/95 px-3 py-2 text-sm text-muted" role="status">
        <LoaderCircle class="animate-spin" :size="16" aria-hidden="true" /> Đang tải video...
      </p>
      <video v-if="!hasLoadError" :src="sourceUrl" class="max-h-[34rem] w-full" controls preload="metadata" @loadeddata="handleLoad" @error="handleError">
        Trình duyệt không hỗ trợ phát video này.
      </video>
      <div v-else class="p-5 text-center text-sm text-white">
        <p role="alert">Không thể tải hoặc phát video này.</p>
        <div class="mt-3 flex flex-wrap justify-center gap-2">
          <a :href="sourceUrl" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg border border-white/30 px-3 py-2 font-semibold text-white hover:bg-white/10">
            <ExternalLink :size="15" aria-hidden="true" /> Mở tệp
          </a>
          <a :href="sourceUrl" :download="resourceName" class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 font-semibold text-white hover:opacity-90">
            <Download :size="15" aria-hidden="true" /> Tải xuống
          </a>
        </div>
      </div>
    </div>

    <div v-else-if="previewKind === 'pdf' && sourceUrl" class="relative">
      <p v-if="isLoading" class="absolute inset-x-0 top-0 z-10 flex items-center justify-center gap-2 bg-white/95 px-3 py-2 text-sm text-muted" role="status">
        <LoaderCircle class="animate-spin" :size="16" aria-hidden="true" /> Đang tải PDF...
      </p>
      <iframe :src="sourceUrl" :title="`Xem trước ${resourceName}`" class="h-[min(70vh,44rem)] min-h-80 w-full" @load="handleLoad" @error="handleError"></iframe>
      <div v-if="hasLoadError" class="flex flex-wrap items-center justify-between gap-3 p-4">
        <p class="text-sm text-muted" role="alert">Không thể tải trình xem PDF.</p>
        <div class="flex gap-2">
          <a :href="sourceUrl" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-navy hover:border-primary hover:text-primary">
            <ExternalLink :size="15" aria-hidden="true" /> Mở tệp
          </a>
          <a :href="sourceUrl" :download="resourceName" class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:opacity-90">
            <Download :size="15" aria-hidden="true" /> Tải xuống
          </a>
        </div>
      </div>
    </div>

    <div v-else class="p-5">
      <div class="flex items-start gap-3">
        <FileText class="mt-0.5 shrink-0 text-muted" :size="20" aria-hidden="true" />
        <div class="min-w-0">
          <p class="break-words text-sm font-semibold text-navy">{{ resourceName }}</p>
          <p class="mt-1 text-sm leading-6 text-muted">
            {{ sourceUrl
              ? (previewKind === 'office'
                ? 'Định dạng này chưa hỗ trợ xem trước trực tiếp. Có thể mở hoặc tải tệp để kiểm tra.'
                : 'Không hỗ trợ xem trước định dạng này. Có thể mở hoặc tải tệp nếu liên kết còn khả dụng.')
              : (rawUrl
                ? 'Đường dẫn tệp không hợp lệ hoặc không an toàn nên không thể xem trước hoặc tải xuống.'
                : 'Tệp chưa có đường dẫn truy cập nên hiện chưa thể xem trước hoặc tải xuống.') }}
          </p>
          <div v-if="sourceUrl" class="mt-3 flex flex-wrap gap-2">
            <a :href="sourceUrl" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-navy hover:border-primary hover:text-primary">
              <ExternalLink :size="15" aria-hidden="true" /> Mở tệp
            </a>
            <a :href="sourceUrl" :download="resourceName" class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:opacity-90">
              <Download :size="15" aria-hidden="true" /> Tải xuống
            </a>
          </div>
        </div>
      </div>
    </div>
  </section>

  <Teleport to="body">
    <div v-if="isZoomed && previewKind === 'image' && sourceUrl" class="fixed inset-0 z-[70] flex items-center justify-center bg-navy/90 p-3 sm:p-8" role="dialog" aria-modal="true" aria-label="Ảnh phóng to" @click.self="isZoomed = false" @keydown.esc="isZoomed = false">
      <button type="button" class="absolute right-4 top-4 flex size-10 items-center justify-center rounded-full bg-white text-navy hover:bg-background" aria-label="Đóng ảnh phóng to" @click="isZoomed = false">
        <X :size="20" aria-hidden="true" />
      </button>
      <img :src="sourceUrl" :alt="resourceName" class="max-h-full max-w-full object-contain" />
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: '',
  },
  label: {
    type: String,
    default: '',
  },
  variant: {
    type: String,
    default: '',
  },
  tone: {
    type: String,
    default: '',
    validator: (value) => ['', 'neutral', 'success', 'warning', 'danger', 'info', 'teal', 'amber', 'navy'].includes(value),
  },
})

// Bảng ánh xạ trạng thái nghiệp vụ EduSuggest chuẩn hóa
const STATUS_MAP = {
  // Trạng thái kiểm duyệt khóa học (Provider & Reviewer)
  ChoKiemDuyet: { tone: 'warning', label: 'Chờ kiểm duyệt' },
  PENDING: { tone: 'warning', label: 'Chờ kiểm duyệt' },
  pending: { tone: 'warning', label: 'Chờ kiểm duyệt' },

  DaPheDuyet: { tone: 'success', label: 'Đã phê duyệt' },
  APPROVED: { tone: 'success', label: 'Đã phê duyệt' },
  approved: { tone: 'success', label: 'Đã phê duyệt' },

  TuChoi: { tone: 'danger', label: 'Từ chối' },
  REJECTED: { tone: 'danger', label: 'Từ chối' },
  rejected: { tone: 'danger', label: 'Từ chối' },

  YeuCauChinhSua: { tone: 'info', label: 'Yêu cầu chỉnh sửa' },
  NEEDS_REVISION: { tone: 'info', label: 'Yêu cầu chỉnh sửa' },
  changesRequested: { tone: 'info', label: 'Yêu cầu chỉnh sửa' },

  Draft: { tone: 'neutral', label: 'Bản nháp' },
  DRAFT: { tone: 'neutral', label: 'Bản nháp' },
  draft: { tone: 'neutral', label: 'Bản nháp' },

  // Trạng thái học tập & Đăng ký
  dang_hoc: { tone: 'teal', label: 'Đang học' },
  in_progress: { tone: 'teal', label: 'Đang học' },
  hoan_thanh: { tone: 'success', label: 'Hoàn thành' },
  completed: { tone: 'success', label: 'Hoàn thành' },
  huy: { tone: 'danger', label: 'Đã hủy' },
  cancelled: { tone: 'danger', label: 'Đã hủy' },

  // Trạng thái hiển thị
  CongKhai: { tone: 'success', label: 'Công khai' },
  VISIBLE: { tone: 'success', label: 'Công khai' },
  public: { tone: 'success', label: 'Công khai' },
  An: { tone: 'neutral', label: 'Đang ẩn' },
  HIDDEN: { tone: 'neutral', label: 'Đang ẩn' },
  private: { tone: 'neutral', label: 'Đang ẩn' },
}

const resolvedTone = computed(() => {
  if (props.tone) return props.tone
  if (props.variant) return props.variant
  if (props.status && STATUS_MAP[props.status]) {
    return STATUS_MAP[props.status].tone
  }
  return 'neutral'
})

const resolvedLabel = computed(() => {
  if (props.label) return props.label
  if (props.status && STATUS_MAP[props.status]) {
    return STATUS_MAP[props.status].label
  }
  return props.status || 'Chưa xác định'
})

const badgeClass = computed(() => `ui-status-badge--${resolvedTone.value}`)
</script>

<template>
  <span class="ui-status-badge" :class="badgeClass">
    <slot>{{ resolvedLabel }}</slot>
  </span>
</template>

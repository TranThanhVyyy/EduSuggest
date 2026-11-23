export const REVIEW_STATUS = Object.freeze({
  pending: 'ChoKiemDuyet',
  approved: 'DaPheDuyet',
  rejected: 'TuChoi',
  changesRequested: 'YeuCauChinhSua',
})

export const REVIEW_STATUS_LABELS = Object.freeze({
  [REVIEW_STATUS.pending]: 'Chờ kiểm duyệt',
  [REVIEW_STATUS.approved]: 'Đã phê duyệt',
  [REVIEW_STATUS.rejected]: 'Từ chối',
  [REVIEW_STATUS.changesRequested]: 'Yêu cầu chỉnh sửa',
})

export const REVIEWABLE_STATUSES = [
  REVIEW_STATUS.pending,
]

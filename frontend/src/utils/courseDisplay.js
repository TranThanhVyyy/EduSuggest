/**
 * Shared course metadata formatting helpers (GĐ5.3).
 * Preserves underlying DB/API enum values (zero impact on TF-IDF Recommendation Engine)
 * while normalizing Vietnamese display across CourseCard, CourseDetail, Catalog, Wishlist, etc.
 */

const LEVEL_LABELS = {
  BEGINNER: 'Cơ bản',
  'CƠ BẢN': 'Cơ bản',
  INTERMEDIATE: 'Trung cấp',
  'TRUNG CẤP': 'Trung cấp',
  ADVANCED: 'Nâng cao',
  'NÂNG CAO': 'Nâng cao',
  ALL_LEVELS: 'Mọi cấp độ',
  'MỌI CẤP ĐỘ': 'Mọi cấp độ',
}

export function formatCourseLevel(raw) {
  if (!raw) return ''
  const key = String(raw).trim().toLocaleUpperCase('vi')
  return LEVEL_LABELS[key] || String(raw).trim()
}

export function formatDurationMinutes(raw) {
  if (raw === null || raw === undefined || raw === '') return ''
  const str = String(raw).trim()
  if (!str || str === 'Chưa có thông tin') return ''
  if (/^\d+$/.test(str)) {
    const mins = Number(str)
    if (mins <= 0) return ''
    if (mins >= 60) {
      const hours = Math.round((mins / 60) * 10) / 10
      const hoursLabel = Number.isInteger(hours) ? `${hours} giờ` : `${hours.toString().replace('.', ',')} giờ`
      return `${mins} phút (${hoursLabel})`
    }
    return `${mins} phút`
  }
  return str
}

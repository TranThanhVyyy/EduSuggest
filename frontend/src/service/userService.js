// User-facing learning APIs are not available in the current Backend.
// Keep these read helpers empty so screens show an honest unavailable state.
export function getUserProfile() { return null }
export function getUserRoles() { return [] }
export function saveUserProfile() { throw new Error('Hồ sơ người học chưa có API cập nhật.') }
export function getPublicCourses() { return [] }
export function getPublicCourse() { return null }
export function getEnrollment() { return null }
export function isEnrolled() { return false }
export function getEnrolledCourses() { return [] }
export function getCourseProgress() { return null }
export function enrollInCourse() { throw new Error('Đăng ký khóa học chưa có API.') }
export function getLearningCourse() { return null }
export function setCurrentLesson() { throw new Error('Tiến độ bài học chưa có API.') }
export function markLessonCompleted() { throw new Error('Tiến độ bài học chưa có API.') }
export function getLearningStats() { return { totalCourses: 0, inProgressCourses: 0, completedCourses: 0, completedLessons: 0 } }
export function getLearningHistory() { return [] }
export function getRecentLearningActivities() { return [] }
export function getPublicMaterials() { return [] }
export function getPublicMaterial() { return null }
export function getRecommendedCourses() { return [] }
export function getRecommendedMaterials() { return [] }
export function getExperts() { return [] }
export function getExpertReviewHistory() { return [] }
export function submitExpertReview() { throw new Error('Đánh giá chuyên gia chưa có API.') }

import api from './api'

export function isProtectedMaterialUrl(value) {
  return /^\/api\/materials\/\d+\/file(?:\?|$)/.test(String(value || ''))
}
function apiRelativePath(value) {
  return String(value).replace(/^\/api/, '')
}

function contentDispositionFilename(headerValue, fallback) {
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(headerValue || '')
  if (encoded?.[1]) {
    try { return decodeURIComponent(encoded[1]) } catch { /* use fallback */ }
  }
  const simple = /filename="?([^";]+)"?/i.exec(headerValue || '')
  return simple?.[1] || fallback
}

export async function openMaterialFile({ id, fileUrl, title }, { download = false } = {}) {
  if (!fileUrl) throw new Error('Tài liệu chưa có tệp đính kèm.')
  if (!isProtectedMaterialUrl(fileUrl)) {
    window.open(fileUrl, '_blank', 'noopener,noreferrer')
    return
  }

  const previewWindow = download ? null : window.open('about:blank', '_blank')
  if (previewWindow) previewWindow.opener = null
  try {
    const { data, headers } = await api.get(apiRelativePath(fileUrl), {
      params: download ? { download: true } : undefined,
      responseType: 'blob',
    })
    const blobUrl = URL.createObjectURL(data)
    if (download) {
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = contentDispositionFilename(headers['content-disposition'], title || `material-${id}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } else if (previewWindow) {
      previewWindow.location.replace(blobUrl)
    } else {
      window.open(blobUrl, '_blank', 'noopener,noreferrer')
    }
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000)
  } catch (error) {
    previewWindow?.close()
    throw error
  }
}

import { ref, uploadBytes } from 'firebase/storage'
import { storage } from '../lib/firebase'
import { api } from './api'
import { getSessionId } from './session'

export function changePostState(userId: string, postId: string, field: 'liked' | 'saved', value: boolean) {
  return api(`/api/v1/me/posts/${encodeURIComponent(postId)}/state`, 'PUT', {
    event_id: crypto.randomUUID(), session_id: getSessionId(userId), field, value,
  }, userId)
}

export async function publishCloudPost(userId: string, postId: string, caption: string, file: File) {
  if (!storage) throw new Error('圖片儲存服務尚未設定')
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) {
    throw new Error('請選擇 10 MB 以下的 JPG、PNG 或 WEBP 圖片')
  }
  const path = `uploads/${userId}/${postId}`
  const result = await api<{ published: boolean }>(`/api/v1/me/posts/${postId}/status`, 'GET', undefined, userId)
  if (result.published) return
  await uploadBytes(ref(storage, path), file, { contentType: file.type })
  await api('/api/v1/me/posts', 'POST', { post_id: postId, caption, image_path: path }, userId)
}

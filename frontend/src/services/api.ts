import { getRequestIdentity } from './auth'

export async function api<T>(path: string, method = 'GET', body?: unknown, expectedUid?: string): Promise<T> {
  const identity = await getRequestIdentity()
  if (!identity.token || (expectedUid && identity.userId !== expectedUid)) throw new Error('請重新登入後再試')
  const response = await fetch(path, {
    method,
    headers: { Authorization: `Bearer ${identity.token}`, 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(data?.error?.message ?? `雲端請求失敗 (${response.status})`)
  return data as T
}

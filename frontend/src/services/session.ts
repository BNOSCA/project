function sessionStorageKey(userId: string) {
  return `loop:session:${userId}:v1`
}

export function getSessionId(userId = 'anonymous-demo') {
  const key = sessionStorageKey(userId)
  const existing = localStorage.getItem(key)

  if (existing) {
    return existing
  }

  const created = crypto.randomUUID()
  localStorage.setItem(key, created)

  return created
}

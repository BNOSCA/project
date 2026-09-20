export function getSessionId(userId = 'anonymous-demo') {
  const key = `loop:session:${userId}:v2`
  let session: { id: string; activeAt: number } | null = null
  try { session = JSON.parse(sessionStorage.getItem(key) ?? 'null') } catch { /* Start a new session. */ }
  if (!session || Date.now() - session.activeAt > 30 * 60 * 1000) {
    session = { id: crypto.randomUUID(), activeAt: Date.now() }
  }
  session.activeAt = Date.now()
  sessionStorage.setItem(key, JSON.stringify(session))
  return session.id
}

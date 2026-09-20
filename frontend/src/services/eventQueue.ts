import { api } from './api'
import { getRequestIdentity } from './auth'

type QueuedEvent = { event_id: string; user_id: string; [key: string]: unknown }
function queueKey(uid: string) { return `loop:event-outbox:${uid}:v1` }
function read(uid: string): QueuedEvent[] {
  const data = JSON.parse(localStorage.getItem(queueKey(uid)) ?? '[]')
  if (!Array.isArray(data)) throw new Error('互動佇列無法讀取')
  return data
}
const flushing = new Set<string>()

export async function flushEvents() {
  const identity = await getRequestIdentity()
  const uid = identity.userId
  if (!identity.token || flushing.has(uid)) return
  flushing.add(uid)
  try {
    const pending = read(uid)
    for (let start = 0; start < pending.length; start += 50) {
      const batch = pending.slice(start, start + 50)
      await api('/api/v1/events/batch', 'POST', batch, uid)
      const sent = new Set(batch.map(e => e.event_id))
      localStorage.setItem(queueKey(uid), JSON.stringify(read(uid).filter(e => !sent.has(e.event_id))))
    }
  } finally { flushing.delete(uid) }
}

export async function enqueueEvents(events: QueuedEvent[]) {
  const identity = await getRequestIdentity()
  if (!identity.token || events.some(e => e.user_id !== identity.userId)) throw new Error('請先登入')
  const pending = new Map(read(identity.userId).map(e => [e.event_id, e]))
  events.forEach(e => pending.set(e.event_id, e))
  localStorage.setItem(queueKey(identity.userId), JSON.stringify([...pending.values()]))
  await flushEvents()
}

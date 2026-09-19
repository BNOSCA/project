import { authenticatedHeaders } from './auth'

export interface AdminStatus {
  is_admin: boolean
}

export interface AdminInsights {
  overview: Record<string, number>
  age_distribution: Record<string, number>
  style_distribution: Record<string, number>
  engagement: Record<string, number>
  rates: Record<string, number>
}

async function adminFetch(path: string) {
  const response = await fetch(path, { headers: await authenticatedHeaders() })
  if (!response.ok) throw new Error(`Admin request failed (${response.status})`)
  return response.json()
}

export async function loadAdminStatus(): Promise<AdminStatus> {
  return adminFetch('/api/v1/admin/status')
}

export async function loadAdminInsights(): Promise<AdminInsights> {
  return adminFetch('/api/v1/admin/insights')
}

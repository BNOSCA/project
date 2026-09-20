import { api } from './api'

export interface AdminStatus { is_admin: boolean }
export interface AdminInsights {
  overview: Record<string, number>
  age_distribution: Record<string, number>
  style_distribution: Record<string, number>
  engagement: Record<string, number>
  rates: Record<string, number>
}
export function loadAdminStatus() { return api<AdminStatus>('/api/v1/admin/status') }
export function loadAdminInsights() { return api<AdminInsights>('/api/v1/admin/insights') }

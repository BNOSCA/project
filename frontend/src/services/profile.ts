import { api } from './api'
import type { User } from '../types'

export const AGE_RANGES = ['18-24', '25-34', '35-44', '45+', '不透露'] as const
export const STYLE_OPTIONS = [
  'japanese', 'korean', 'minimal', 'streetwear', 'casual', 'outdoor',
  'sporty', 'vintage', 'preppy', 'techwear', 'old_money',
] as const
export type AgeRange = typeof AGE_RANGES[number]
export type StyleOption = typeof STYLE_OPTIONS[number]
export interface CloudUserProfile {
  user_id: string
  age_range?: AgeRange
  preferred_styles: StyleOption[]
  onboarding_completed: boolean
  followed_creator_ids?: string[]
  public_profile?: Pick<User, 'displayName' | 'username' | 'bio' | 'avatarUrl'>
}
export interface AccountState {
  profile: CloudUserProfile | null
  liked_ids: string[]
  saved_ids: string[]
}
export function loadAccount(userId: string) {
  return api<AccountState>('/api/v1/me', 'GET', undefined, userId)
}
export async function loadUserProfile(userId: string) {
  return (await loadAccount(userId)).profile
}
export function saveOnboardingProfile(userId: string, profile: Pick<CloudUserProfile, 'age_range' | 'preferred_styles'>) {
  return api('/api/v1/me/onboarding', 'PUT', profile, userId)
}
export function savePublicProfile(userId: string, profile: Pick<User, 'displayName' | 'username' | 'bio' | 'avatarUrl'>) {
  return api('/api/v1/me/public-profile', 'PUT', profile, userId)
}

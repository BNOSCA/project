import { doc, getDoc, setDoc, serverTimestamp } from 'firebase/firestore'

import { db } from '../lib/firebase'

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
}

export async function loadUserProfile(userId: string): Promise<CloudUserProfile | null> {
  if (!db) return null
  const snapshot = await getDoc(doc(db, 'users', userId))
  if (!snapshot.exists()) return null
  return { user_id: userId, preferred_styles: [], onboarding_completed: false, ...snapshot.data() } as CloudUserProfile
}

export async function saveOnboardingProfile(
  userId: string,
  profile: Pick<CloudUserProfile, 'age_range' | 'preferred_styles'>,
) {
  if (!db) throw new Error('Firebase 尚未設定')
  await setDoc(doc(db, 'users', userId), {
    user_id: userId,
    age_range: profile.age_range,
    preferred_styles: profile.preferred_styles,
    onboarding_completed: true,
    updated_at: serverTimestamp(),
  }, { merge: true })
}

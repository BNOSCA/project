import { signInAnonymously } from 'firebase/auth'

import { auth, isFirebaseConfigured } from '../lib/firebase'

export interface RequestIdentity {
  userId: string
  token: string | null
}

let identityPromise: Promise<RequestIdentity> | null = null

/** Return the stable Firebase uid used to scope recommendations and interactions. */
export function getRequestIdentity(): Promise<RequestIdentity> {
  if (identityPromise) return identityPromise

  identityPromise = (async () => {
    if (!isFirebaseConfigured || !auth) {
      return { userId: 'anonymous-demo', token: null }
    }

    const user = auth.currentUser ?? (await signInAnonymously(auth)).user
    return { userId: user.uid, token: await user.getIdToken() }
  })().catch(error => {
    identityPromise = null
    throw error
  })

  return identityPromise
}

export async function authenticatedHeaders(): Promise<HeadersInit> {
  const { token } = await getRequestIdentity()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

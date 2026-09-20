import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  updateProfile,
  type User as FirebaseUser,
} from 'firebase/auth'

import { auth, isFirebaseConfigured } from '../lib/firebase.ts'

export interface RequestIdentity {
  userId: string
  token: string | null
}

export interface AuthState {
  user: FirebaseUser | null
  loading: boolean
  configured: boolean
}

let identityPromise: Promise<RequestIdentity> | null = null
const AUTH_REQUEST_TIMEOUT_MS = 15_000

async function withAuthTimeout<T>(operation: Promise<T>): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      const error = new Error('Firebase 驗證服務逾時，請確認網路與 Firebase Authentication 設定。')
      Object.assign(error, { code: 'auth/timeout' })
      reject(error)
    }, AUTH_REQUEST_TIMEOUT_MS)
  })
  try {
    return await Promise.race([operation, timeout])
  } finally {
    if (timeoutId) clearTimeout(timeoutId)
  }
}

export function observeAuthState(listener: (state: AuthState) => void) {
  if (!auth || !isFirebaseConfigured) {
    listener({ user: null, loading: false, configured: false })
    return () => {}
  }

  listener({ user: auth.currentUser, loading: true, configured: true })
  return onAuthStateChanged(auth, user => {
    listener({ user, loading: false, configured: true })
  })
}

export async function signInWithEmail(email: string, password: string) {
  if (!auth) throw new Error('Firebase 尚未設定')
  return (await withAuthTimeout(signInWithEmailAndPassword(auth, email, password))).user
}

export async function createAccount(
  email: string,
  password: string,
  displayName: string,
) {
  if (!auth) throw new Error('Firebase 尚未設定')
  const credential = await withAuthTimeout(createUserWithEmailAndPassword(auth, email, password))
  await withAuthTimeout(updateProfile(credential.user, { displayName }))
  identityPromise = null
  return credential.user
}

export async function signInWithGoogle() {
  if (!auth) throw new Error('Firebase 尚未設定')
  return (await withAuthTimeout(signInWithPopup(auth, new GoogleAuthProvider()))).user
}

export async function requestPasswordReset(email: string) {
  if (!auth) throw new Error('Firebase 尚未設定')
  await withAuthTimeout(sendPasswordResetEmail(auth, email))
}

export async function saveFirebaseProfile(displayName: string, photoURL?: string) {
  if (!auth?.currentUser) throw new Error('請先登入')
  await updateProfile(auth.currentUser, {
    displayName,
    photoURL: photoURL || null,
  })
}

export async function signOutCurrentUser() {
  if (!auth) return
  await signOut(auth)
}

export async function getRequestIdentity(): Promise<RequestIdentity> {
  await auth?.authStateReady()
  const user = auth?.currentUser
  if (!user || user.isAnonymous) return { userId: 'anonymous-demo', token: null }
  return { userId: user.uid, token: await user.getIdToken() }
}

export async function authenticatedHeaders(): Promise<HeadersInit> {
  const { token } = await getRequestIdentity()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

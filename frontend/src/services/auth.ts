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

import { auth, isFirebaseConfigured } from '../lib/firebase'

export interface RequestIdentity {
  userId: string
  token: string | null
}

export interface AuthState {
  user: FirebaseUser | null
  loading: boolean
  configured: boolean
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
  return (await signInWithEmailAndPassword(auth, email, password)).user
}

export async function createAccount(
  email: string,
  password: string,
  displayName: string,
) {
  if (!auth) throw new Error('Firebase 尚未設定')
  const credential = await createUserWithEmailAndPassword(auth, email, password)
  await updateProfile(credential.user, { displayName })
  return credential.user
}

export async function signInWithGoogle() {
  if (!auth) throw new Error('Firebase 尚未設定')
  return (await signInWithPopup(auth, new GoogleAuthProvider())).user
}

export async function requestPasswordReset(email: string) {
  if (!auth) throw new Error('Firebase 尚未設定')
  await sendPasswordResetEmail(auth, email)
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

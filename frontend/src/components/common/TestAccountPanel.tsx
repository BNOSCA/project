import { signInWithEmailAndPassword, signOut } from 'firebase/auth'
import { type FormEvent, useState } from 'react'

import { auth, isFirebaseConfigured } from '../../lib/firebase'

/** Development-only helper for switching between Firebase test accounts. */
export function TestAccountPanel() {
  const [email, setEmail] = useState('test0@demo.com')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const firebaseAuth = auth

  if (!import.meta.env.DEV || !isFirebaseConfigured || !firebaseAuth) return null

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!firebaseAuth) return
    setMessage('登入中…')
    try {
      await signInWithEmailAndPassword(firebaseAuth, email.trim(), password)
      window.location.reload()
    } catch {
      setMessage('登入失敗，請確認 Email、密碼與 Firebase Email/Password 已啟用。')
    }
  }

  async function useAnonymousAccount() {
    if (!firebaseAuth) return
    await signOut(firebaseAuth)
    window.location.reload()
  }

  return (
    <form className="test-account-panel" onSubmit={submit}>
      <span>測試帳號</span>
      <input value={email} onChange={event => setEmail(event.target.value)} type="email" aria-label="測試帳號 Email" />
      <input value={password} onChange={event => setPassword(event.target.value)} type="password" placeholder="密碼" aria-label="測試帳號密碼" />
      <button type="submit">登入</button>
      <button type="button" onClick={() => void useAnonymousAccount()}>匿名測試</button>
      {message && <small>{message}</small>}
    </form>
  )
}

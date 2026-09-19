import { useEffect, useState, type FormEvent } from 'react'
import { Eye, EyeOff, LockKeyhole, Mail, UserRound, X } from 'lucide-react'

import {
  createAccount,
  requestPasswordReset,
  signInWithEmail,
  signInWithGoogle,
} from '../../services/auth'

interface AuthDialogProps {
  open: boolean
  configured: boolean
  onClose: () => void
  onSuccess: (message: string) => void
}

type AuthMode = 'login' | 'register'

function authErrorMessage(error: unknown) {
  const code = typeof error === 'object' && error && 'code' in error
    ? String(error.code)
    : ''

  if (code.includes('invalid-credential')) return 'Email 或密碼不正確。'
  if (code.includes('email-already-in-use')) return '這個 Email 已經註冊過。'
  if (code.includes('weak-password')) return '密碼至少需要 6 個字元。'
  if (code.includes('invalid-email')) return '請輸入有效的 Email。'
  if (code.includes('popup-closed')) return 'Google 登入視窗已關閉。'
  if (code.includes('popup-blocked')) return '瀏覽器阻擋了登入視窗。'
  return error instanceof Error ? error.message : '登入時發生問題，請稍後再試。'
}

export function AuthDialog({ open, configured, onClose, onSuccess }: AuthDialogProps) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    setError('')
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [open, onClose])

  if (!open) return null

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      if (mode === 'register') {
        await createAccount(email.trim(), password, displayName.trim())
        onSuccess('帳號建立完成，歡迎加入 LOOP')
      } else {
        await signInWithEmail(email.trim(), password)
        onSuccess('登入成功')
      }
      onClose()
    } catch (authError) {
      setError(authErrorMessage(authError))
    } finally {
      setSubmitting(false)
    }
  }

  async function resetPassword() {
    if (!email.trim()) {
      setError('請先輸入 Email。')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await requestPasswordReset(email.trim())
      onSuccess('密碼重設信已寄出')
    } catch (authError) {
      setError(authErrorMessage(authError))
    } finally {
      setSubmitting(false)
    }
  }

  async function googleLogin() {
    setSubmitting(true)
    setError('')
    try {
      await signInWithGoogle()
      onSuccess('Google 登入成功')
      onClose()
    } catch (authError) {
      setError(authErrorMessage(authError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={event => {
      if (event.target === event.currentTarget) onClose()
    }}>
      <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <button className="icon-button dialog-close" type="button" onClick={onClose} aria-label="關閉">
          <X size={20} />
        </button>

        <div className="auth-brand">LOOP</div>
        <h1 id="auth-title">{mode === 'login' ? '歡迎回來' : '建立你的帳號'}</h1>
        <p>{mode === 'login' ? '登入後同步你的收藏與穿搭偏好。' : '開始收藏靈感，建立專屬風格檔案。'}</p>

        {!configured ? (
          <div className="auth-config-notice">目前尚未設定 Firebase，請完成環境設定後啟用登入。</div>
        ) : (
          <>
            <button className="google-button" type="button" disabled={submitting} onClick={googleLogin}>
              <span>G</span>
              使用 Google 繼續
            </button>

            <div className="auth-divider"><span>或使用 Email</span></div>

            <form className="auth-form" onSubmit={submit}>
              {mode === 'register' && (
                <label>
                  顯示名稱
                  <span>
                    <UserRound size={17} />
                    <input value={displayName} onChange={event => setDisplayName(event.target.value)} autoComplete="name" required placeholder="你的名稱" />
                  </span>
                </label>
              )}
              <label>
                Email
                <span>
                  <Mail size={17} />
                  <input type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="email" required placeholder="name@example.com" />
                </span>
              </label>
              <label>
                密碼
                <span>
                  <LockKeyhole size={17} />
                  <input type={showPassword ? 'text' : 'password'} value={password} onChange={event => setPassword(event.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={6} required placeholder="至少 6 個字元" />
                  <button type="button" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? '隱藏密碼' : '顯示密碼'}>
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </span>
              </label>

              {mode === 'login' && <button className="text-button forgot-button" type="button" onClick={resetPassword}>忘記密碼？</button>}
              {error && <div className="form-error" role="alert">{error}</div>}
              <button className="primary-button auth-submit" type="submit" disabled={submitting}>
                {submitting ? '處理中...' : mode === 'login' ? '登入' : '建立帳號'}
              </button>
            </form>
          </>
        )}

        <div className="auth-switch">
          {mode === 'login' ? '還沒有帳號？' : '已經有帳號？'}
          <button type="button" onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login')
            setError('')
          }}>
            {mode === 'login' ? '立即註冊' : '返回登入'}
          </button>
        </div>
      </section>
    </div>
  )
}

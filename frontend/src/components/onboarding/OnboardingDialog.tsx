import { useState } from 'react'

import {
  AGE_RANGES,
  STYLE_OPTIONS,
  type AgeRange,
  type StyleOption,
} from '../../services/profile'

interface OnboardingDialogProps {
  open: boolean
  onComplete: (ageRange: AgeRange, styles: StyleOption[]) => Promise<void>
}

const styleLabels: Record<StyleOption, string> = {
  japanese: '日系', korean: '韓系', minimal: '極簡', streetwear: '街頭',
  casual: '休閒', outdoor: '戶外', sporty: '運動', vintage: '復古',
  preppy: '學院', techwear: '機能', old_money: 'Old Money',
}

export function OnboardingDialog({ open, onComplete }: OnboardingDialogProps) {
  const [ageRange, setAgeRange] = useState<AgeRange>('不透露')
  const [styles, setStyles] = useState<StyleOption[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (!open) return null

  function toggleStyle(style: StyleOption) {
    setStyles(current => current.includes(style)
      ? current.filter(item => item !== style)
      : [...current, style])
  }

  async function submit() {
    setSaving(true)
    setError('')
    try {
      await onComplete(ageRange, styles)
    } catch (caughtError) {
      const detail = caughtError instanceof Error ? caughtError.message : ''
      setError(detail ? `儲存偏好失敗：${detail}` : '儲存偏好失敗，請稍後再試。')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="onboarding-backdrop">
      <section className="onboarding-dialog" role="dialog" aria-modal="true" aria-labelledby="onboarding-title">
        <div className="eyebrow">WELCOME TO LOOP</div>
        <h1 id="onboarding-title">先告訴我們你的風格</h1>
        <p>只需要兩個選擇，之後推薦會更貼近你。</p>

        <label className="onboarding-label" htmlFor="onboarding-age">年齡區間</label>
        <select id="onboarding-age" value={ageRange} onChange={event => setAgeRange(event.target.value as AgeRange)}>
          {AGE_RANGES.map(value => <option key={value} value={value}>{value}</option>)}
        </select>

        <div className="onboarding-label">喜歡的風格</div>
        <div className="style-choice-grid">
          {STYLE_OPTIONS.map(style => (
            <button
              key={style}
              type="button"
              className={styles.includes(style) ? 'style-choice selected' : 'style-choice'}
              onClick={() => toggleStyle(style)}
              aria-pressed={styles.includes(style)}
            >
              {styleLabels[style]}
            </button>
          ))}
        </div>
        {error && <div className="form-error">{error}</div>}
        <button className="primary-button onboarding-submit" type="button" onClick={() => void submit()} disabled={saving}>
          {saving ? '儲存中...' : '開始探索'}
        </button>
      </section>
    </div>
  )
}

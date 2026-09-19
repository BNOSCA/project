import {
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import {
  type FormEvent,
  useState,
} from 'react'

import {
  recommend,
  type RecommendResponse,
} from '../../services/recommendation'
import { QuerySuggestionChips } from './QuerySuggestionChips'

const suggestions = [
  '面試穿搭',
  '約會',
  '日系',
  '夏天',
  '3000元內',
]

interface AIQueryBarProps {
  onResult: (response: RecommendResponse) => void
  onStart: () => void
  onError: (message: string) => void
  isLoading: boolean
}

export function AIQueryBar({
  onResult,
  onStart,
  onError,
  isLoading,
}: AIQueryBarProps) {
  const [query, setQuery] = useState('')

  function applySuggestion(suggestion: string) {
    const suggestionText = suggestion === '約會'
      ? '想找約會穿搭'
      : `想找${suggestion}`

    setQuery(current => current.trim()
      ? `${current.trim()}，${suggestionText}`
      : suggestionText)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const text = query.trim()
    if (!text || isLoading) {
      return
    }

    onStart()

    try {
      const response = await recommend({
        session_id: `web-${crypto.randomUUID()}`,
        text,
        user_id: 'anonymous-demo',
        filters: {},
        image: null,
      })

      onResult(response)
    } catch {
      onError('目前無法取得推薦，請稍後再試。')
    }
  }

  return (
    <div className="ai-query-panel">
      <div className="ai-query-heading">
        <span><Sparkles size={15} /> AI 穿搭靈感</span>
        <h1>今天想穿什麼？</h1>
        <p>把場合、預算和感覺一次告訴我。</p>
      </div>

      <form className="ai-query-form" onSubmit={submit}>
        <Sparkles className="query-sparkle" size={19} aria-hidden="true" />
        <input
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="例如：週末約會，預算 2500，想日系一點"
          aria-label="描述你想找的穿搭"
          disabled={isLoading}
        />
        <button
          type="submit"
          aria-label="取得穿搭推薦"
          disabled={!query.trim() || isLoading}
        >
          <ArrowRight size={20} />
        </button>
      </form>

      <QuerySuggestionChips
        suggestions={suggestions}
        onSelect={applySuggestion}
      />
    </div>
  )
}

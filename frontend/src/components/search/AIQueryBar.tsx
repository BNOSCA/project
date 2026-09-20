import {
  ArrowRight,
  ImagePlus,
  Sparkles,
} from 'lucide-react'
import {
  type FormEvent,
  useRef,
  useState,
} from 'react'

import {
  searchCatalogProducts,
  type CatalogSearchResult,
} from '../../services/feed'
import {
  recommend,
  type RecommendResponse,
} from '../../services/recommendation'
import { getRequestIdentity } from '../../services/auth'
import { getSessionId } from '../../services/session'
import { QuerySuggestionChips } from './QuerySuggestionChips'

const suggestions = [
  '面試穿搭',
  '約會',
  '日系',
  '夏天',
  '3000元內',
]

interface AIQueryBarProps {
  onResult: (response: CatalogSearchResult) => void
  onRecommendation: (response: RecommendResponse) => void
  onStart: () => void
  onError: (message: string) => void
  isLoading: boolean
}

export function AIQueryBar({
  onResult,
  onRecommendation,
  onStart,
  onError,
  isLoading,
}: AIQueryBarProps) {
  const [query, setQuery] = useState('')
  const [queryImage, setQueryImage] = useState<string | null>(null)
  const [imageName, setImageName] = useState('')
  const imageInput = useRef<HTMLInputElement>(null)

  function applySuggestion(suggestion: string) {
    const suggestionText = suggestion === '約會'
      ? '想找約會穿搭'
      : `想找${suggestion}`

    setQuery(current => current.trim()
      ? `${current.trim()}，${suggestionText}`
      : suggestionText)
  }

  function chooseImage(file: File | undefined) {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      onError('請選擇圖片檔案。')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      setQueryImage(typeof reader.result === 'string' ? reader.result : null)
      setImageName(file.name)
    }
    reader.onerror = () => onError('圖片讀取失敗，請換一張圖片再試。')
    reader.readAsDataURL(file)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const text = query.trim()
    if ((!text && !queryImage) || isLoading) {
      return
    }

    onStart()

    try {
      const response = await searchCatalogProducts({
        queryText: text,
        queryImage,
        filters: { availableOnly: true },
      })

      onResult(response)
      if (response.recommendation) {
        onRecommendation(response.recommendation)
      } else if (text) {
        // Support a frontend deployed ahead of the API rollout: older search
        // responses do not yet contain tag-derived outfits.
        void getRequestIdentity()
          .then(identity => recommend({
            session_id: getSessionId(identity.userId),
            text,
          }))
          .then(onRecommendation)
          .catch(() => {})
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : '目前無法取得推薦，請稍後再試。')
    }
  }

  return (
    <div className="ai-query-panel">
      <div className="ai-query-heading">
        <span><Sparkles size={15} /> AI 穿搭靈感</span>
        <h1>今天想穿什麼？</h1>
        <p>用文字、參考圖片或兩者一起找相似單品。</p>
      </div>

      <form className="ai-query-form" onSubmit={submit}>
        <Sparkles className="query-sparkle" size={19} aria-hidden="true" />
        <input
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="例如：日系 寬鬆 襯衫"
          aria-label="描述你想找的商品"
          disabled={isLoading}
        />
        <input ref={imageInput} className="visually-hidden" type="file"
          accept="image/*" onChange={event => chooseImage(event.target.files?.[0])} />
        <button type="button" className="query-image-button"
          aria-label="上傳參考圖片" title="上傳參考圖片"
          disabled={isLoading} onClick={() => imageInput.current?.click()}>
          <ImagePlus size={18} />
        </button>
        <button
          type="submit"
          aria-label="搜尋相似商品"
          disabled={(!query.trim() && !queryImage) || isLoading}
        >
          <ArrowRight size={20} />
        </button>
      </form>

      {imageName && (
        <div className="query-image-status">
          <span>參考圖：{imageName}</span>
          <button type="button" onClick={() => {
            setQueryImage(null)
            setImageName('')
            if (imageInput.current) imageInput.current.value = ''
          }}>移除</button>
        </div>
      )}

      <QuerySuggestionChips
        suggestions={suggestions}
        onSelect={applySuggestion}
      />
    </div>
  )
}

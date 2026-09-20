import {
  Sparkles,
} from 'lucide-react'
import { useState } from 'react'

import type {
  RecommendedOutfit,
  RecommendResponse,
} from '../../services/recommendation'
import { recordProductClick } from '../../services/feed'
import { ParsedIntentChips } from './ParsedIntentChips'

const swatches = ['#d8e0e3', '#55575a', '#e8e1d4']

function OutfitPiece({ item, index }: {
  item: RecommendedOutfit['items'][number]
  index: number
}) {
  const [imageFailed, setImageFailed] = useState(false)
  return item.image_url && !imageFailed ? (
    <img src={item.image_url} alt={item.name} onError={() => setImageFailed(true)} />
  ) : (
    <div className="recommendation-piece"
      style={{ backgroundColor: swatches[index % swatches.length] }}>
      <span>{item.category}</span>
      <strong>{item.name}</strong>
    </div>
  )
}

function OutfitCard({
  outfit,
}: {
  outfit: RecommendedOutfit
}) {
  return (
    <article className="recommendation-card">
      <div className="recommendation-visual">
        {outfit.items.slice(0, 3).map((item, index) => (
          <OutfitPiece key={item.product_id} item={item} index={index} />
        ))}
      </div>
      <div className="recommendation-copy">
        <div>
          <span>完整穿搭</span>
          <strong>NT${outfit.total_price.toLocaleString()}</strong>
        </div>
        <p>依本次搜尋標籤，組合上衣、下身與鞋款。</p>
        <ul className="recommendation-products">
          {outfit.items.map(item => (
            <li key={item.product_id}>
              {item.product_url ? (
                <a href={item.product_url} target="_blank" rel="noopener noreferrer"
                  onClick={() => { void recordProductClick(item.product_id).catch(() => {}) }}>
                  {item.name} · NT${item.price.toLocaleString()} ↗
                </a>
              ) : (
                <span>{item.name} · NT${item.price.toLocaleString()}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    </article>
  )
}

export function RecommendationSkeleton() {
  return (
    <section className="recommendation-section" aria-busy="true">
      <div className="recommendation-title">
        <span><Sparkles size={15} /> 正在理解你的需求...</span>
      </div>
      <div className="recommendation-grid">
        {[0, 1, 2].map(item => (
          <div className="recommendation-skeleton" key={item}>
            <div />
            <span />
            <span />
          </div>
        ))}
      </div>
    </section>
  )
}

export function RecommendationResults({
  response,
}: {
  response: RecommendResponse
}) {
  const needsClarification = response.needs_clarification
    ?? response.intent.needs_clarification
  const clarifyingQuestion = response.clarifying_question
    ?? response.intent.clarifying_question

  return (
    <section className="recommendation-section">
      <div className="recommendation-title">
        <span>你的需求</span>
        <ParsedIntentChips intent={response.intent} />
      </div>

      {needsClarification && clarifyingQuestion ? (
        <div className="clarification-card">
          <Sparkles size={18} />
          <div>
            <strong>再確認一下</strong>
            <p>{clarifyingQuestion}</p>
            <small>你可以直接修改上方需求後重新送出。</small>
          </div>
        </div>
      ) : response.outfits.length === 0 ? (
        <div className="recommendation-empty">
          <strong>暫時找不到完全符合條件的穿搭</strong>
          <p>可以調整預算或限制再試一次。</p>
        </div>
      ) : (
        <>
          <div className="recommendation-heading-row">
            <h2>推薦穿搭</h2>
            <span>{response.outfits.length} 套結果</span>
          </div>
          <div className="recommendation-grid">
            {response.outfits.map(outfit => (
              <OutfitCard key={outfit.outfit_id} outfit={outfit} />
            ))}
          </div>
          {response.message && <p className="recommendation-disclaimer">{response.message}</p>}
        </>
      )}
    </section>
  )
}

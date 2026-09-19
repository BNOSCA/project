import type { RecommendationIntent } from '../../services/recommendation'

const occasionLabels: Record<string, string> = {
  date: '約會',
  interview: '面試',
  office: '上班',
  weekend: '週末',
}

const styleLabels: Record<string, string> = {
  Japanese: '日系',
  Korean: '韓系',
  Minimal: '極簡',
}

interface ParsedIntentChipsProps {
  intent: RecommendationIntent
}

export function ParsedIntentChips({
  intent,
}: ParsedIntentChipsProps) {
  const chips = [
    ...intent.occasion.map(value => occasionLabels[value] ?? value),
    ...(intent.budget_total === null
      ? []
      : [`預算 ≤ NT$${intent.budget_total.toLocaleString()}`]),
    ...intent.preferred.styles.map(value => styleLabels[value] ?? value),
    ...intent.preferred.fits,
    ...(intent.semantic_query ? [intent.semantic_query] : []),
  ]

  return (
    <div className="intent-chips" aria-label="AI 理解的需求">
      {chips.map((chip, index) => (
        <span key={`${chip}-${index}`}>{chip}</span>
      ))}
    </div>
  )
}

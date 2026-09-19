import { getMockRecommendation } from '../data/mockRecommendation'

export interface RecommendRequest {
  session_id: string
  text: string
  user_id?: string
  filters?: Record<string, unknown>
  image?: string | null
}

export interface RecommendationAttributes {
  styles: string[]
  colors: string[]
  fits: string[]
  materials: string[]
}

export interface RecommendationIntent {
  occasion: string[]
  budget_total: number | null
  currency?: string
  preferred: RecommendationAttributes
  excluded: Omit<RecommendationAttributes, 'styles'>
  semantic_query: string
  needs_clarification?: boolean
  clarifying_question?: string | null
}

export interface RecommendedProduct {
  product_id: string
  name: string
  category: string
  price: number
  currency?: string
  colors?: string[]
  styles?: string[]
  image_url?: string | null
}

export interface RecommendedOutfit {
  outfit_id: string
  items: RecommendedProduct[]
  total_price: number
  reason: string
  warnings?: string[]
}

export interface RecommendResponse {
  session_id: string
  intent: RecommendationIntent
  outfits: RecommendedOutfit[]
  message?: string | null
  needs_clarification?: boolean
  clarifying_question?: string | null
}

const useDevelopmentMock =
  import.meta.env.DEV &&
  import.meta.env.VITE_USE_MOCK_RECOMMENDATION !== 'false'

export async function recommend(
  request: RecommendRequest,
): Promise<RecommendResponse> {
  if (useDevelopmentMock) {
    return getMockRecommendation(request)
  }

  const response = await fetch('/api/v1/recommend', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...request,
      user_id: request.user_id ?? 'anonymous-demo',
      filters: request.filters ?? {},
      image: request.image ?? null,
    }),
  })

  if (!response.ok) {
    throw new Error('Recommendation request failed')
  }

  return response.json() as Promise<RecommendResponse>
}

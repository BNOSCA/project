import type { OutfitItemCategory } from './fashion'

export interface Product {
  id: string

  brand: string
  name: string

  category: OutfitItemCategory

  color: string

  price: number

  imageUrl?: string
  productUrl?: string

  similarity?: number

  similarityExplanation?: string
  similarityExplanationSource?: 'llm' | 'fallback'

  matchType?: 'exact' | 'similar'
}

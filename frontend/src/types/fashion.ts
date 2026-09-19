export type OutfitItemCategory =
  | 'top'
  | 'bottom'
  | 'outerwear'
  | 'shoes'
  | 'bag'
  | 'accessory'

export interface OutfitItem {
  id: string

  category: OutfitItemCategory

  name: string
  color: string

  material?: string
  style?: string
}

export interface Outfit {
  id: string

  name: string
  description: string

  items: OutfitItem[]

  styles: string[]
  occasions: string[]

  season?: string[]
  formality?: number
}
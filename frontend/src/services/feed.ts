import type {
  OutfitItemCategory,
  OutfitPost,
  Product,
} from '../types'
import { getSessionId } from './session.ts'
import { authenticatedHeaders, getRequestIdentity } from './auth.ts'

interface ApiPost {
  post_id: string
  creator_id: string
  image_url?: string | null
  caption: string
  styles: string[]
  colors: string[]
  occasion: string[]
  item_tags: string[]
  engagement: {
    like_count: number
    save_count: number
    comment_count: number
  }
  created_at?: string | null
}

interface ApiFeedResponse {
  items: Array<{
    score: number
    post: ApiPost | null
    creator?: { display_name: string } | null
  }>
}

export function demoSessionId() {
  return getSessionId()
}

function itemCategory(tag: string): OutfitItemCategory {
  const value = tag.toLowerCase()

  if (value.includes('shoe') || value.includes('sneaker')) return 'shoes'
  if (value.includes('bag')) return 'bag'
  if (value.includes('coat') || value.includes('jacket')) return 'outerwear'
  if (value.includes('pant') || value.includes('skirt') || value.includes('bottom')) return 'bottom'
  if (value.includes('hat') || value.includes('accessory')) return 'accessory'
  return 'top'
}

function itemName(tag: string): string {
  const names: Record<string, string> = {
    top: '上衣', bottom: '下身', shoes: '鞋款', outerwear: '外套',
    bag: '包款', accessory: '配件',
  }
  return names[tag.toLowerCase()] ?? tag
}

function toOutfitPost(post: ApiPost, score: number, creatorDisplayName?: string): OutfitPost {
  const tags = post.item_tags.length > 0 ? post.item_tags : ['Outfit']
  const creatorName = creatorDisplayName ?? post.creator_id.replace(/^creator-/, '').replaceAll('-', ' ')

  return {
    id: post.post_id,
    author: {
      id: post.creator_id,
      username: post.creator_id.replace(/^creator-/, ''),
      displayName: creatorName,
      avatarText: creatorName.slice(0, 2).toUpperCase(),
      postCount: 1,
      followerCount: 0,
      followingCount: 0,
    },
    caption: post.caption,
    imageUrl: post.image_url ?? undefined,
    outfit: {
      id: `outfit-${post.post_id}`,
      name: post.styles[0] ? `${post.styles[0]} OOTD` : 'Daily OOTD',
      description: post.caption,
      styles: post.styles,
      occasions: post.occasion,
      items: tags.map((tag, index) => ({
        id: `${post.post_id}-item-${index}`,
        category: itemCategory(tag),
        name: itemName(tag),
        color: post.colors[index % Math.max(post.colors.length, 1)] ?? '#d8d3ca',
        style: post.styles[0],
      })),
    },
    stats: {
      likeCount: post.engagement.like_count,
      saveCount: post.engagement.save_count,
      commentCount: post.engagement.comment_count,
    },
    viewerState: { liked: false, saved: false },
    matchScore: Math.round(Math.max(0, Math.min(1, score)) * 100),
    createdAt: post.created_at ?? new Date().toISOString(),
  }
}

export async function loadRecommendedFeed(): Promise<OutfitPost[]> {
  const [identity, authHeaders] = await Promise.all([
    getRequestIdentity(),
    authenticatedHeaders(),
  ])
  const query = new URLSearchParams({
    user_id: identity.userId,
    session_id: getSessionId(identity.userId),
    limit: '20',
  })
  const response = await fetch(`/api/v1/feed?${query}`, { headers: authHeaders })

  if (!response.ok) {
    throw new Error(`Feed request failed (${response.status})`)
  }

  const data = (await response.json()) as ApiFeedResponse
  return data.items
    .filter((item): item is typeof item & { post: ApiPost } => item.post !== null)
    .map(item => toOutfitPost(item.post, item.score, item.creator?.display_name))
}

interface ApiCatalogProduct {
  product_id: string
  name: string
  category: string
  brand?: string | null
  source_name?: string | null
  price: number | null
  colors: string[]
  image_url?: string | null
  product_url?: string | null
}

interface ApiPostDetail {
  tagged_products: Array<{
    match_type: 'exact' | 'similar'
    product: ApiCatalogProduct
  }>
  similar_products: ApiCatalogProduct[]
  similar_product_explanations?: Record<string, string>
  similar_product_explanation_sources?: Record<string, 'llm' | 'fallback'>
}

function catalogCategory(value: string): OutfitItemCategory {
  if (value === 'top' || value === 'bottom' || value === 'shoes' ||
      value === 'outerwear' || value === 'bag' || value === 'accessory') {
    return value
  }
  return 'accessory'
}

function catalogProduct(
  item: ApiCatalogProduct,
  matchType?: 'exact' | 'similar',
  similarityExplanation?: string,
  similarityExplanationSource?: 'llm' | 'fallback',
): Product | null {
  if (item.price === null) return null
  const imageUrl = item.image_url
    ? (item.image_url.startsWith('http') || item.image_url.startsWith('/')
        ? item.image_url
        : `/products/catalog/${encodeURIComponent(item.product_id)}.jpg`)
    : undefined
  return {
    id: item.product_id,
    brand: item.brand ?? item.source_name ?? '展示商品',
    name: item.name,
    category: catalogCategory(item.category),
    color: item.colors[0] === 'off_white' ? '#f5f4ef' : (item.colors[0] ?? '#d8d3ca'),
    price: item.price,
    imageUrl,
    productUrl: item.product_url ?? undefined,
    similarity: (item as any).similarity ?? (matchType === 'exact' ? 96 : 91),
    ...(matchType ? { matchType } : {}),
    ...(similarityExplanation ? { similarityExplanation } : {}),
    ...(similarityExplanationSource ? { similarityExplanationSource } : {}),
  }
}

export async function loadPostProducts(postId: string): Promise<Product[]> {
  const response = await fetch(`/api/v1/posts/${encodeURIComponent(postId)}`)
  if (!response.ok) throw new Error(`Post detail failed (${response.status})`)
  const detail = (await response.json()) as ApiPostDetail
  const products = [
    ...detail.tagged_products.map(tag => ({
      item: tag.product,
      matchType: tag.match_type,
      explanation: undefined,
      explanationSource: undefined,
    })),
    ...detail.similar_products.map((item, idx) => ({
      item: {
        ...item,
        similarity: (item as ApiCatalogProduct & { similarity?: number }).similarity
          ?? Math.max(78, 96 - idx * 3),
      },
      matchType: 'similar' as const,
      explanation: detail.similar_product_explanations?.[item.product_id],
      explanationSource: detail.similar_product_explanation_sources?.[item.product_id],
    })),
  ]
  const unique = new Set<string>()
  return products.flatMap(({ item, matchType, explanation, explanationSource }) => {
    if (unique.has(item.product_id)) return []
    unique.add(item.product_id)
    const product = catalogProduct(item, matchType, explanation, explanationSource)
    return product ? [product] : []
  })
}

export interface CatalogSearchResult {
  products: Product[]
  fusionMethod: string
  candidateCount: number
}

export interface CatalogSearchFilters {
  category?: string
  priceMax?: number
  availableOnly?: boolean
  excludedColors?: string[]
  excludedFits?: string[]
  sizes?: string[]
}

export interface CatalogSearchRequest {
  queryText?: string
  queryImage?: string | null
  imageWeight?: number
  filters?: CatalogSearchFilters
}

export function searchCatalogProducts(request: CatalogSearchRequest): Promise<CatalogSearchResult>
/** @deprecated Pass a CatalogSearchRequest so image search can be specified. */
export function searchCatalogProducts(queryText: string, filters?: CatalogSearchFilters): Promise<CatalogSearchResult>
export async function searchCatalogProducts(
  requestOrQuery: CatalogSearchRequest | string,
  legacyFilters: CatalogSearchFilters = {},
): Promise<CatalogSearchResult> {
  const request = typeof requestOrQuery === 'string'
    ? { queryText: requestOrQuery, filters: legacyFilters }
    : requestOrQuery
  const queryText = request.queryText?.trim() ?? ''
  const queryImage = request.queryImage ?? null
  const filters = request.filters ?? {}
  const mode = queryImage
    ? (queryText ? 'mixed' : 'image')
    : 'text'
  const [identity, authHeaders] = await Promise.all([
    getRequestIdentity(),
    authenticatedHeaders(),
  ])
  const response = await fetch('/api/v1/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders },
    body: JSON.stringify({
      session_id: getSessionId(identity.userId),
      query_text: queryText,
      query_image: queryImage,
      mode,
      image_weight: request.imageWeight ?? 0.5,
      filters: {
        categories: filters.category ? [filters.category] : [],
        ...(filters.priceMax ? { price_max: filters.priceMax } : {}),
        ...(filters.availableOnly ? { available_only: true } : {}),
        ...(filters.excludedColors?.length ? { excluded_colors: filters.excludedColors } : {}),
        ...(filters.excludedFits?.length ? { excluded_fits: filters.excludedFits } : {}),
        ...(filters.sizes?.length ? { sizes: filters.sizes } : {}),
      },
    }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as
      | { error?: { message?: string } }
      | null
    throw new Error(body?.error?.message ?? `商品搜尋失敗 (${response.status})`)
  }
  const data = await response.json() as {
    products: Array<{
      product: ApiCatalogProduct | null
      score: number
      explanation?: string | null
      explanation_source?: 'llm' | 'fallback' | 'none'
    }>
    retrieval: { fusion_method: string; prefilter_count: number }
  }
  return {
    products: data.products.flatMap(hit => {
      if (!hit.product) return []
      const product = catalogProduct(hit.product)
      return product ? [{
        ...product,
        similarity: Math.round(hit.score * 100),
        ...(hit.explanation ? { similarityExplanation: hit.explanation } : {}),
        ...(hit.explanation_source === 'llm' || hit.explanation_source === 'fallback'
          ? { similarityExplanationSource: hit.explanation_source }
          : {}),
      }] : []
    }),
    fusionMethod: data.retrieval.fusion_method,
    candidateCount: data.retrieval.prefilter_count,
  }
}

async function postJson(path: string, body: unknown) {
  const authHeaders = await authenticatedHeaders()
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Interaction request failed (${response.status})`)
  }
}

export function recordPostLike(postId: string) {
  return getRequestIdentity().then(identity => postJson('/api/v1/feedback', {
    event_id: crypto.randomUUID(),
    session_id: getSessionId(identity.userId),
    user_id: identity.userId,
    event_type: 'like',
    target_type: 'post',
    target_id: postId,
  }))
}

export function recordPostSave(postId: string) {
  return getRequestIdentity().then(identity => postJson('/api/v1/events/batch', [{
    event_id: crypto.randomUUID(),
    session_id: getSessionId(identity.userId),
    user_id: identity.userId,
    event_type: 'save',
    target_type: 'post',
    target_id: postId,
    surface: 'home-feed',
    is_foreground: true,
  }]))
}

export function recordPostInteraction(
  postId: string,
  eventType: 'post_open' | 'dwell',
  dwellMs?: number,
) {
  return getRequestIdentity().then(identity => postJson('/api/v1/events/batch', [{
    event_id: crypto.randomUUID(),
    session_id: getSessionId(identity.userId),
    user_id: identity.userId,
    event_type: eventType,
    target_type: 'post',
    target_id: postId,
    surface: 'home-feed',
    is_foreground: true,
    ...(dwellMs === undefined ? {} : { dwell_ms: dwellMs }),
  }]))
}

export function recordPostImpression(postId: string, position: number) {
  return getRequestIdentity().then(identity => postJson('/api/v1/events/batch', [{
    event_id: `impression:${identity.userId}:${postId}`,
    session_id: getSessionId(identity.userId),
    user_id: identity.userId,
    event_type: 'impression',
    target_type: 'post',
    target_id: postId,
    surface: 'home-feed',
    position,
    is_foreground: document.visibilityState === 'visible',
  }]))
}

export function recordProductClick(productId: string) {
  return getRequestIdentity().then(identity => postJson('/api/v1/events/batch', [{
    event_id: crypto.randomUUID(),
    session_id: getSessionId(identity.userId),
    user_id: identity.userId,
    event_type: 'product_click',
    target_type: 'product',
    target_id: productId,
    surface: 'post-products',
    is_foreground: true,
  }]))
}

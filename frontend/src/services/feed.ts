import type {
  OutfitItemCategory,
  OutfitPost,
} from '../types'

const userId = 'anonymous-demo'
const sessionStorageKey = 'loop:feed-session:v1'

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
  }>
}

function feedSessionId() {
  const existing = localStorage.getItem(sessionStorageKey)

  if (existing) {
    return existing
  }

  const created = crypto.randomUUID()
  localStorage.setItem(sessionStorageKey, created)
  return created
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

function toOutfitPost(post: ApiPost, score: number): OutfitPost {
  const tags = post.item_tags.length > 0 ? post.item_tags : ['Outfit']
  const creatorName = post.creator_id.replace(/^creator-/, '').replaceAll('-', ' ')

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
        name: tag,
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
  const query = new URLSearchParams({
    user_id: userId,
    session_id: feedSessionId(),
    limit: '20',
  })
  const response = await fetch(`/api/v1/feed?${query}`)

  if (!response.ok) {
    throw new Error(`Feed request failed (${response.status})`)
  }

  const data = (await response.json()) as ApiFeedResponse
  return data.items
    .filter((item): item is typeof item & { post: ApiPost } => item.post !== null)
    .map(item => toOutfitPost(item.post, item.score))
}

async function postJson(path: string, body: unknown) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Interaction request failed (${response.status})`)
  }
}

export function recordPostLike(postId: string) {
  return postJson('/api/v1/feedback', {
    event_id: crypto.randomUUID(),
    session_id: feedSessionId(),
    user_id: userId,
    event_type: 'like',
    target_type: 'post',
    target_id: postId,
  })
}

export function recordPostSave(postId: string) {
  return postJson('/api/v1/events/batch', [{
    event_id: crypto.randomUUID(),
    session_id: feedSessionId(),
    user_id: userId,
    event_type: 'save',
    target_type: 'post',
    target_id: postId,
    surface: 'home-feed',
    is_foreground: true,
  }])
}

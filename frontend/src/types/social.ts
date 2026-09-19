import type { OutfitPost } from './post'

export interface Friend {
  id: string
  displayName: string
  username: string
  email: string
  avatarText: string
  avatarUrl?: string
  styleTags?: string[]
  matchPercentage?: number
  connectedAt: string
}

export interface SharedOutfit {
  id: string
  postId: string
  fromUser: {
    id: string
    displayName: string
    avatarText: string
    avatarUrl?: string
  }
  toFriendId: string
  toFriendName: string
  message: string
  matchPercentage?: number
  sharedAt: string
  post: OutfitPost
}

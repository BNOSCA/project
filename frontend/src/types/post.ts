import type { Outfit } from './fashion'
import type { User } from './user'

export interface PostStats {
  likeCount: number
  commentCount: number
  saveCount: number
}

export interface PostViewerState {
  liked: boolean
  saved: boolean
}

export interface OutfitPost {
  id: string

  author: User

  caption: string

  imageUrl?: string

  outfit: Outfit

  stats: PostStats

  viewerState: PostViewerState

  matchScore?: number

  createdAt: string
}
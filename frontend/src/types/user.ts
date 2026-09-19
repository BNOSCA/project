export interface User {
  id: string

  username: string
  displayName: string

  avatarText: string
  avatarUrl?: string

  bio?: string

  postCount: number
  followerCount: number
  followingCount: number

  verified?: boolean
}
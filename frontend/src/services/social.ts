import type { Friend, SharedOutfit } from '../types/social'
import type { OutfitPost, User } from '../types/index'
import { db, auth } from '../lib/firebase'
import { collection, doc, getDocs, setDoc, deleteDoc } from 'firebase/firestore'

const DEFAULT_FRIENDS: Friend[] = [
  {
    id: 'friend-elena',
    displayName: 'Elena Lin',
    username: 'elena_style',
    email: 'elena.style@example.com',
    avatarText: 'EL',
    avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    styleTags: ['街頭極簡', '黑白色系'],
    matchPercentage: 96,
    connectedAt: '2026-09-18',
  },
  {
    id: 'friend-marcus',
    displayName: 'Marcus Chen',
    username: 'marcus_wear',
    email: 'marcus.c@example.com',
    avatarText: 'MC',
    avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    styleTags: ['戶外運動', '機能街頭'],
    matchPercentage: 91,
    connectedAt: '2026-09-19',
  },
  {
    id: 'friend-sophie',
    displayName: 'Sophie Wang',
    username: 'sophie_daily',
    email: 'sophie.w@example.com',
    avatarText: 'SW',
    avatarUrl: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80',
    styleTags: ['復古學院', '簡約文藝'],
    matchPercentage: 94,
    connectedAt: '2026-09-19',
  },
  {
    id: 'friend-lucas',
    displayName: 'Lucas Wu',
    username: 'lucas_style',
    email: 'lucas.wu@example.com',
    avatarText: 'LW',
    avatarUrl: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
    styleTags: ['極簡都會', '質感疊穿'],
    matchPercentage: 88,
    connectedAt: '2026-09-20',
  },
]

function getStorageKey(userId: string): string {
  return `intentloop:friends:${userId || 'anonymous'}`
}

function loadLocalFriends(userId: string): Friend[] {
  try {
    const raw = localStorage.getItem(getStorageKey(userId))
    if (!raw) {
      localStorage.setItem(getStorageKey(userId), JSON.stringify(DEFAULT_FRIENDS))
      return DEFAULT_FRIENDS
    }
    return JSON.parse(raw) as Friend[]
  } catch {
    return DEFAULT_FRIENDS
  }
}

function saveLocalFriends(userId: string, friends: Friend[]): void {
  try {
    localStorage.setItem(getStorageKey(userId), JSON.stringify(friends))
  } catch (error) {
    console.error('Failed to save friends to localStorage', error)
  }
}

export async function getFriends(userId: string): Promise<Friend[]> {
  // If Firebase Firestore is active and user is logged in
  if (db && auth?.currentUser) {
    try {
      const colRef = collection(db, 'users', auth.currentUser.uid, 'friends')
      const snapshot = await getDocs(colRef)
      if (!snapshot.empty) {
        const remoteFriends = snapshot.docs.map(d => d.data() as Friend)
        saveLocalFriends(userId, remoteFriends)
        return remoteFriends
      }
    } catch (err) {
      console.warn('Firestore fetch failed, using local storage fallback', err)
    }
  }

  return loadLocalFriends(userId)
}

export async function addFriendByEmail(userId: string, email: string): Promise<Friend> {
  const normalizedEmail = email.trim().toLowerCase()
  const localList = loadLocalFriends(userId)

  // Check if already connected
  const existing = localList.find(f => f.email.toLowerCase() === normalizedEmail)
  if (existing) {
    throw new Error('此郵箱已經在您的好友名單中！')
  }

  // Derive nickname and username
  const prefix = normalizedEmail.split('@')[0] || 'Friend'
  const displayName = prefix.charAt(0).toUpperCase() + prefix.slice(1).replace(/[._-]/g, ' ')
  const username = prefix.replace(/[^a-zA-Z0-9_]/g, '_')
  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(p => p[0].toUpperCase())
    .join('') || prefix.slice(0, 2).toUpperCase()

  // Random style match between 78% and 96%
  const randomMatch = Math.floor(Math.random() * 19) + 78
  const sampleTags = [
    ['日系休閒', '寬鬆版型'],
    ['俐落都會', '極簡黑白'],
    ['街頭工裝', '休閒復古'],
    ['輕戶外風', '露營機能'],
  ]
  const pickedTags = sampleTags[Math.floor(Math.random() * sampleTags.length)]

  const newFriend: Friend = {
    id: `friend-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    displayName,
    username,
    email: normalizedEmail,
    avatarText: initials,
    styleTags: pickedTags,
    matchPercentage: randomMatch,
    connectedAt: new Date().toISOString().split('T')[0],
  }

  const updated = [newFriend, ...localList]
  saveLocalFriends(userId, updated)
  const updatedList = [newFriend, ...localList]
  saveLocalFriends(userId, updatedList)

  // Sync with Firestore if active
  if (db && auth?.currentUser) {
    try {
      const docRef = doc(db, 'users', auth.currentUser.uid, 'friends', newFriend.id)
      await setDoc(docRef, newFriend)
    } catch (err) {
      console.warn('Failed to sync new friend to Firestore', err)
    }
  }

  return newFriend
}

export async function removeFriend(userId: string, friendId: string): Promise<void> {
  const localList = loadLocalFriends(userId)
  const updated = localList.filter(f => f.id !== friendId)
  saveLocalFriends(userId, updated)
  const updatedList = localList.filter(f => f.id !== friendId)
  saveLocalFriends(userId, updatedList)

  // Delete from Firestore if active
  if (db && auth?.currentUser) {
    try {
      const docRef = doc(db, 'users', auth.currentUser.uid, 'friends', friendId)
      await deleteDoc(docRef)
    } catch (err) {
      console.warn('Failed to remove friend from Firestore', err)
    }
  }
}

// -------------------------------------------------------------
// Shared Outfits (好友穿搭分享箱)
// -------------------------------------------------------------

function getSharedStorageKey(userId: string): string {
  return `intentloop:shared_outfits:${userId || 'anonymous'}`
}

export function buildDefaultSharedOutfits(userId: string): SharedOutfit[] {
  return [
    {
      id: 'share-seed-01',
      postId: 'post-seed-01',
      fromUser: {
        id: 'friend-elena',
        displayName: 'Elena Lin',
        avatarText: 'EL',
        avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
      },
      toFriendId: userId,
      toFriendName: 'You',
      message: '這套日系大地色亞麻襯衫搭配很適合今天！材質很透氣～',
      matchPercentage: 95,
      sharedAt: '2 小時前',
      post: {
        id: 'post-seed-elena',
        author: {
          id: 'friend-elena',
          username: 'elena_ootd',
          displayName: 'Elena Lin',
          avatarText: 'EL',
          avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
          postCount: 12,
          followerCount: 240,
          followingCount: 180,
        },
        imageUrl: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&auto=format&fit=crop&q=80',
        caption: '初秋微風日系簡約搭配，大地色寬版襯衫 × 垂墜感九分西褲。',
        createdAt: '2026-09-19',
        matchScore: 0.95,
        stats: { likeCount: 42, commentCount: 5, saveCount: 18 },
        viewerState: { liked: false, saved: false },
        outfit: {
          id: 'outfit-elena-01',
          name: '日系大地色透氣休閒穿搭',
          description: '透氣舒適的日系亞麻襯衫，搭配垂墜感打褶西褲。',
          styles: ['japanese', 'minimal', 'relaxed'],
          occasions: ['casual', 'weekend'],
          items: [
            {
              id: 'item-e-01',
              name: '亞麻混紡寬版長袖襯衫',
              category: 'top',
              color: 'beige',
              style: 'relaxed',
            },
            {
              id: 'item-e-02',
              name: '垂墜感寬版打褶長褲',
              category: 'bottom',
              color: 'brown',
              style: 'relaxed',
            },
          ],
        },
      },
    },
    {
      id: 'share-seed-02',
      postId: 'post-seed-02',
      fromUser: {
        id: 'friend-marcus',
        displayName: 'Marcus Chen',
        avatarText: 'MC',
        avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
      },
      toFriendId: userId,
      toFriendName: 'You',
      message: '看看這套山系工裝，防潑水多口袋外套機能感滿分！',
      matchPercentage: 89,
      sharedAt: '昨天',
      post: {
        id: 'post-seed-marcus',
        author: {
          id: 'friend-marcus',
          username: 'marcus_wear',
          displayName: 'Marcus Chen',
          avatarText: 'MC',
          avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
          postCount: 28,
          followerCount: 512,
          followingCount: 320,
        },
        imageUrl: 'https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?w=600&auto=format&fit=crop&q=80',
        caption: '山系機能日常穿搭，多口袋工裝連帽外套 × 防撕裂尼龍縮口褲。',
        createdAt: '2026-09-18',
        matchScore: 0.89,
        stats: { likeCount: 89, commentCount: 12, saveCount: 35 },
        viewerState: { liked: false, saved: false },
        outfit: {
          id: 'outfit-marcus-01',
          name: '山系機能防風日常搭配',
          description: '抗撕裂多口袋登山外套，兼具機能防風與街頭帥氣。',
          styles: ['outdoor', 'workwear'],
          occasions: ['outdoor', 'casual'],
          items: [
            {
              id: 'item-m-01',
              name: '防潑水連帽登山外套',
              category: 'outerwear',
              color: 'olive',
              style: 'outdoor',
            },
            {
              id: 'item-m-02',
              name: '多口袋抗撕裂工裝束口褲',
              category: 'bottom',
              color: 'black',
              style: 'workwear',
            },
          ],
        },
      },
    },
    {
      id: 'share-seed-03',
      postId: 'post-seed-03',
      fromUser: {
        id: 'friend-sophie',
        displayName: 'Sophie Wang',
        avatarText: 'SW',
        avatarUrl: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80',
      },
      toFriendId: userId,
      toFriendName: 'You',
      message: '這套法式極簡條紋長袖搭配高腰直筒牛仔褲，隨性又俐落！',
      matchPercentage: 92,
      sharedAt: '前天',
      post: {
        id: 'post-seed-sophie',
        author: {
          id: 'friend-sophie',
          username: 'sophie_daily',
          displayName: 'Sophie Wang',
          avatarText: 'SW',
          avatarUrl: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80',
          postCount: 19,
          followerCount: 380,
          followingCount: 210,
        },
        imageUrl: 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=600&auto=format&fit=crop&q=80',
        caption: '法式極簡復古摩登穿搭，經典橫條紋針織長袖 × 復古直筒牛仔褲。',
        createdAt: '2026-09-17',
        matchScore: 0.92,
        stats: { likeCount: 65, commentCount: 8, saveCount: 29 },
        viewerState: { liked: false, saved: false },
        outfit: {
          id: 'outfit-sophie-01',
          name: '俐落法式條紋摩登搭配',
          description: '法式黑白經典橫條紋長袖，搭配高腰修身直筒牛仔褲。',
          styles: ['french', 'minimal', 'smart casual'],
          occasions: ['work', 'brunch', 'weekend'],
          items: [
            {
              id: 'item-s-01',
              name: '法式經典橫條紋長袖針織衫',
              category: 'top',
              color: 'black',
              style: 'minimal',
            },
            {
              id: 'item-s-02',
              name: '復古高腰直筒牛仔長褲',
              category: 'bottom',
              color: 'blue',
              style: 'classic',
            },
            {
              id: 'item-s-03',
              name: '經典牛皮深色樂福鞋',
              category: 'shoes',
              color: 'brown',
              style: 'classic',
            },
          ],
        },
      },
    },
  ]
}

export function loadLocalSharedOutfits(userId: string): SharedOutfit[] {
  try {
    const raw = localStorage.getItem(getSharedStorageKey(userId))
    if (!raw) {
      const defaults = buildDefaultSharedOutfits(userId)
      localStorage.setItem(getSharedStorageKey(userId), JSON.stringify(defaults))
      return defaults
    }
    return JSON.parse(raw) as SharedOutfit[]
  } catch {
    return []
  }
}

export function resetSharedOutfits(userId: string): SharedOutfit[] {
  const defaults = buildDefaultSharedOutfits(userId)
  localStorage.setItem(getSharedStorageKey(userId), JSON.stringify(defaults))
  return defaults
}

export function saveLocalSharedOutfits(userId: string, list: SharedOutfit[]): void {
  try {
    localStorage.setItem(getSharedStorageKey(userId), JSON.stringify(list))
  } catch (err) {
    console.error('Failed to save shared outfits', err)
  }
}

export async function getSharedOutfits(userId: string): Promise<SharedOutfit[]> {
  return loadLocalSharedOutfits(userId)
}

export async function shareOutfitToFriend(
  userId: string,
  currentUser: User,
  friend: Friend,
  post: OutfitPost,
  message?: string
): Promise<SharedOutfit> {
  const currentList = loadLocalSharedOutfits(userId)

  const newShare: SharedOutfit = {
    id: `share-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    postId: post.id,
    fromUser: {
      id: currentUser.id,
      displayName: currentUser.displayName,
      avatarText: currentUser.avatarText,
      avatarUrl: currentUser.avatarUrl,
    },
    toFriendId: friend.id,
    toFriendName: friend.displayName,
    post,
    message: message || `推薦給你這套「${post.outfit?.name || post.caption || '精選穿搭'}」！`,
    matchPercentage: friend.matchPercentage || 85,
    sharedAt: '剛剛',
  }

  const updated = [newShare, ...currentList]
  saveLocalSharedOutfits(userId, updated)
  return newShare
}

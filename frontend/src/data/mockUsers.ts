import type { User } from '../types/index'

export const mockUsers: User[] = [
  {
    id: 'user-john',
    username: 'john.style',
    displayName: 'John',
    avatarText: 'J',

    bio: 'Daily fits, smart casual and whatever works in Taipei weather.',

    postCount: 24,
    followerCount: 1248,
    followingCount: 328,
  },

  {
    id: 'user-mia',
    username: 'mia.wardrobe',
    displayName: 'Mia',
    avatarText: 'M',

    bio: 'Minimal wardrobe · office looks · neutral colors',

    postCount: 86,
    followerCount: 8240,
    followingCount: 412,

    verified: true,
  },

  {
    id: 'user-sean',
    username: 'sean.daily',
    displayName: 'Sean',
    avatarText: 'S',

    bio: 'Everyday menswear and relaxed tailoring.',

    postCount: 57,
    followerCount: 3150,
    followingCount: 521,
  },

  {
    id: 'user-yuna',
    username: 'yuna.fit',
    displayName: 'Yuna',
    avatarText: 'Y',

    bio: 'Seoul / Taipei · clean outfits · daily OOTD',

    postCount: 109,
    followerCount: 12800,
    followingCount: 270,

    verified: true,
  },

  {
    id: 'user-leo',
    username: 'leo.archive',
    displayName: 'Leo',
    avatarText: 'L',

    bio: 'Streetwear, sneakers and archive pieces.',

    postCount: 73,
    followerCount: 5630,
    followingCount: 688,
  },
]

export const currentUser = mockUsers[0]
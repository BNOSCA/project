import type { OutfitPost } from '../types/index'

import { mockUsers } from './mockUsers'

export const mockPosts: OutfitPost[] = [
  {
    id: 'post-001',

    author: mockUsers[1],

    caption:
      '最近最常穿的 office look。天氣熱的時候還是喜歡乾淨、寬鬆一點。',

    outfit: {
      id: 'outfit-001',

      name: 'Minimal Office',

      description:
        '白襯衫搭配深色寬褲與樂福鞋，維持正式感但不會太成熟。',

      styles: [
        'Minimal',
        'Smart Casual',
      ],

      occasions: [
        'Office',
        'Interview',
      ],

      season: [
        'Spring',
        'Summer',
      ],

      formality: 0.72,

      items: [
        {
          id: 'item-001-top',

          category: 'top',

          name: 'White Oxford Shirt',

          color: '#ecebe6',

          material: 'Cotton',

          style: 'Minimal',
        },

        {
          id: 'item-001-bottom',

          category: 'bottom',

          name: 'Navy Wide Trousers',

          color: '#313844',

          material: 'Polyester',

          style: 'Smart Casual',
        },

        {
          id: 'item-001-shoes',

          category: 'shoes',

          name: 'Brown Loafers',

          color: '#604739',

          material: 'Leather',

          style: 'Classic',
        },
      ],
    },

    stats: {
      likeCount: 1248,
      commentCount: 18,
      saveCount: 361,
    },

    viewerState: {
      liked: false,
      saved: false,
    },

    matchScore: 94,

    createdAt: '2026-09-18T22:00:00+08:00',
  },

  {
    id: 'post-002',

    author: mockUsers[2],

    caption:
      '週末不想想太多的搭配。T-shirt、寬褲、球鞋就夠了。',

    outfit: {
      id: 'outfit-002',

      name: 'Weekend Casual',

      description:
        '黑色上衣搭配灰色寬褲與復古球鞋，簡單但有比例。',

      styles: [
        'Casual',
        'Minimal',
      ],

      occasions: [
        'Weekend',
        'School',
        'Coffee',
      ],

      season: [
        'Spring',
        'Summer',
        'Autumn',
      ],

      formality: 0.25,

      items: [
        {
          id: 'item-002-top',

          category: 'top',

          name: 'Black Relaxed T-Shirt',

          color: '#252525',

          material: 'Cotton',

          style: 'Casual',
        },

        {
          id: 'item-002-bottom',

          category: 'bottom',

          name: 'Grey Wide Pants',

          color: '#8b8b87',

          style: 'Minimal',
        },

        {
          id: 'item-002-shoes',

          category: 'shoes',

          name: 'Retro Sneakers',

          color: '#dedbd3',

          style: 'Sporty',
        },
      ],
    },

    stats: {
      likeCount: 832,
      commentCount: 12,
      saveCount: 204,
    },

    viewerState: {
      liked: false,
      saved: false,
    },

    matchScore: 91,

    createdAt: '2026-09-18T19:30:00+08:00',
  },

  {
    id: 'post-003',

    author: mockUsers[3],

    caption:
      '今天全部用低彩度，最近很喜歡灰、奶油白跟深藍一起出現。',

    outfit: {
      id: 'outfit-003',

      name: 'Seoul Neutral',

      description:
        '柔和的米白上衣搭配灰色長裙／寬褲概念與乾淨白鞋。',

      styles: [
        'Korean',
        'Minimal',
        'Neutral',
      ],

      occasions: [
        'Date',
        'Cafe',
        'Daily',
      ],

      season: [
        'Spring',
        'Autumn',
      ],

      formality: 0.42,

      items: [
        {
          id: 'item-003-top',

          category: 'top',

          name: 'Cream Knit Top',

          color: '#dfd6c7',

          style: 'Korean',
        },

        {
          id: 'item-003-bottom',

          category: 'bottom',

          name: 'Charcoal Long Bottom',

          color: '#555657',

          style: 'Minimal',
        },

        {
          id: 'item-003-shoes',

          category: 'shoes',

          name: 'Clean White Sneakers',

          color: '#eeeeea',

          style: 'Minimal',
        },
      ],
    },

    stats: {
      likeCount: 2189,
      commentCount: 34,
      saveCount: 687,
    },

    viewerState: {
      liked: false,
      saved: false,
    },

    matchScore: 89,

    createdAt: '2026-09-18T17:20:00+08:00',
  },

  {
    id: 'post-004',

    author: mockUsers[4],

    caption:
      '最近又開始穿 archive-inspired streetwear，但還是希望不要太複雜。',

    outfit: {
      id: 'outfit-004',

      name: 'Clean Streetwear',

      description:
        '深色外套、寬褲與球鞋形成街頭輪廓，但配色維持簡潔。',

      styles: [
        'Streetwear',
        'Archive',
      ],

      occasions: [
        'Street',
        'Weekend',
        'Concert',
      ],

      season: [
        'Autumn',
        'Winter',
      ],

      formality: 0.18,

      items: [
        {
          id: 'item-004-outerwear',

          category: 'outerwear',

          name: 'Black Zip Jacket',

          color: '#252526',

          style: 'Streetwear',
        },

        {
          id: 'item-004-bottom',

          category: 'bottom',

          name: 'Wide Cargo Pants',

          color: '#484a45',

          style: 'Streetwear',
        },

        {
          id: 'item-004-shoes',

          category: 'shoes',

          name: 'Chunky Sneakers',

          color: '#dad7cf',

          style: 'Streetwear',
        },
      ],
    },

    stats: {
      likeCount: 1642,
      commentCount: 29,
      saveCount: 482,
    },

    viewerState: {
      liked: false,
      saved: false,
    },

    matchScore: 82,

    createdAt: '2026-09-18T13:45:00+08:00',
  },

  {
    id: 'post-005',

    author: mockUsers[2],

    caption:
      '如果真的要面試，我比較想穿成這樣。正式，但不要像借來的西裝。',

    outfit: {
      id: 'outfit-005',

      name: 'Young Interview',

      description:
        '淺藍襯衫、深灰西裝褲與乾淨皮鞋，適合實習或第一份工作的面試。',

      styles: [
        'Business Casual',
        'Clean',
      ],

      occasions: [
        'Interview',
        'Presentation',
        'Office',
      ],

      season: [
        'Spring',
        'Summer',
      ],

      formality: 0.8,

      items: [
        {
          id: 'item-005-top',

          category: 'top',

          name: 'Light Blue Shirt',

          color: '#c8d6df',

          style: 'Business Casual',
        },

        {
          id: 'item-005-bottom',

          category: 'bottom',

          name: 'Dark Grey Trousers',

          color: '#47494d',

          style: 'Business Casual',
        },

        {
          id: 'item-005-shoes',

          category: 'shoes',

          name: 'Black Leather Shoes',

          color: '#282625',

          style: 'Classic',
        },
      ],
    },

    stats: {
      likeCount: 936,
      commentCount: 16,
      saveCount: 408,
    },

    viewerState: {
      liked: false,
      saved: false,
    },

    matchScore: 96,

    createdAt: '2026-09-17T21:10:00+08:00',
  },

  {
    id: 'post-006',

    author: mockUsers[1],

    caption:
      '30°C 的日子還是得穿長褲的話，我現在最常用這種組合。',

    outfit: {
      id: 'outfit-006',

      name: 'Hot Weather Minimal',

      description:
        '輕薄短袖上衣配寬鬆長褲，保留俐落輪廓但降低炎熱感。',

      styles: [
        'Minimal',
        'Summer',
      ],

      occasions: [
        'Daily',
        'Office',
        'Travel',
      ],

      season: [
        'Summer',
      ],

      formality: 0.4,

      items: [
        {
          id: 'item-006-top',

          category: 'top',

          name: 'White AIRism Tee',

          color: '#eeeeea',

          style: 'Minimal',
        },

        {
          id: 'item-006-bottom',

          category: 'bottom',

          name: 'Olive Relaxed Trousers',

          color: '#777769',

          style: 'Minimal',
        },

        {
          id: 'item-006-shoes',

          category: 'shoes',

          name: 'Grey Sneakers',

          color: '#bdbdb8',

          style: 'Casual',
        },
      ],
    },

    stats: {
      likeCount: 1409,
      commentCount: 21,
      saveCount: 553,
    },

    viewerState: {
      liked: false,
      saved: false,
    },

    matchScore: 93,

    createdAt: '2026-09-17T15:00:00+08:00',
  },
]
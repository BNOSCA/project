import type {
  RecommendRequest,
  RecommendResponse,
} from '../services/recommendation'

const mockResponse: Omit<RecommendResponse, 'session_id'> = {
  intent: {
    occasion: ['date'],
    budget_total: 2500,
    currency: 'TWD',
    preferred: {
      styles: ['Japanese'],
      colors: [],
      fits: ['relaxed'],
      materials: [],
    },
    excluded: {
      colors: [],
      fits: [],
      materials: [],
    },
    semantic_query: '不要太正式',
  },
  outfits: [
    {
      outfit_id: 'mock-outfit-001',
      total_price: 2380,
      reason: '寬鬆襯衫與直筒褲保留日系層次，配色乾淨，適合輕鬆的週末約會。',
      items: [
        {
          product_id: 'mock-001-top',
          name: '霧藍寬版襯衫',
          category: 'top',
          price: 780,
          colors: ['霧藍'],
          styles: ['Japanese'],
        },
        {
          product_id: 'mock-001-bottom',
          name: '炭灰直筒長褲',
          category: 'bottom',
          price: 920,
          colors: ['炭灰'],
          styles: ['Minimal'],
        },
        {
          product_id: 'mock-001-shoes',
          name: '奶油白帆布鞋',
          category: 'shoes',
          price: 680,
          colors: ['奶油白'],
          styles: ['Casual'],
        },
      ],
    },
    {
      outfit_id: 'mock-outfit-002',
      total_price: 2490,
      reason: '輕薄針織搭配卡其寬褲，輪廓有質感但不會顯得過度正式。',
      items: [
        {
          product_id: 'mock-002-top',
          name: '米白輕薄針織',
          category: 'top',
          price: 850,
          colors: ['米白'],
          styles: ['Japanese'],
        },
        {
          product_id: 'mock-002-bottom',
          name: '深卡其寬褲',
          category: 'bottom',
          price: 980,
          colors: ['深卡其'],
          styles: ['Relaxed'],
        },
        {
          product_id: 'mock-002-shoes',
          name: '復古德訓鞋',
          category: 'shoes',
          price: 660,
          colors: ['灰白'],
          styles: ['Retro'],
        },
      ],
    },
    {
      outfit_id: 'mock-outfit-003',
      total_price: 2260,
      reason: '短版外套增加造型感，內搭與寬褲維持舒服、年輕的約會氛圍。',
      items: [
        {
          product_id: 'mock-003-outerwear',
          name: '橄欖綠短版外套',
          category: 'outerwear',
          price: 990,
          colors: ['橄欖綠'],
          styles: ['Japanese'],
        },
        {
          product_id: 'mock-003-bottom',
          name: '黑色打褶寬褲',
          category: 'bottom',
          price: 740,
          colors: ['黑'],
          styles: ['Minimal'],
        },
        {
          product_id: 'mock-003-shoes',
          name: '低筒休閒鞋',
          category: 'shoes',
          price: 530,
          colors: ['灰'],
          styles: ['Casual'],
        },
      ],
    },
  ],
  message: '開發模式示範資料',
}

export async function getMockRecommendation(
  request: RecommendRequest,
): Promise<RecommendResponse> {
  await new Promise(resolve => setTimeout(resolve, 850))

  return {
    ...mockResponse,
    session_id: request.session_id,
  }
}

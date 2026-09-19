import test from 'node:test'
import assert from 'node:assert/strict'

import { getMockRecommendation } from '../frontend/src/data/mockRecommendation.ts'
import {
  demoSessionId,
  loadPostProducts,
  recordPostInteraction,
  searchCatalogProducts,
} from '../frontend/src/services/feed.ts'

test('開發 Mock 遵守 recommendation contract 並保留 session id', async () => {
  const response = await getMockRecommendation({
    session_id: 'test-session',
    text: '任意自然語言需求',
  })

  assert.equal(response.session_id, 'test-session')
  assert.ok(response.outfits.length > 0)
  assert.ok(Array.isArray(response.intent.occasion))
  assert.ok(Array.isArray(response.intent.preferred.styles))

  for (const outfit of response.outfits) {
    assert.ok(outfit.outfit_id)
    assert.ok(outfit.reason)
    assert.ok(outfit.items.length > 0)
    assert.equal(
      outfit.total_price,
      outfit.items.reduce((sum, item) => sum + item.price, 0),
    )
  }
})

test('Mock 是固定 UI fixture，不在前端解析 query', async () => {
  const response = await getMockRecommendation({
    session_id: 'no-parser',
    text: '這句話不應被前端關鍵字解析',
  })

  assert.equal(response.intent.occasion[0], 'date')
  assert.equal(response.intent.budget_total, 2500)
  assert.equal(response.intent.semantic_query, '不要太正式')
})

test('貼文商品使用 API 配對、標示相似並略過無價格項目', async () => {
  const previousFetch = globalThis.fetch
  const requests: string[] = []
  globalThis.fetch = (async (url: string) => {
    requests.push(url)
    return new Response(JSON.stringify({
      tagged_products: [{
        match_type: 'similar',
        product: {
          product_id: 'official-1', name: '示範襯衫', category: 'top',
          brand: 'GU', price: 690, colors: ['off_white'],
          image_url: 'https://example.com/item.jpg',
          product_url: 'https://example.com/item',
        },
      }],
      similar_products: [
        { product_id: 'official-1', name: '重複', category: 'top', price: 690, colors: [] },
        { product_id: 'unpriced', name: '未標價', category: 'top', price: null, colors: [] },
      ],
    }), { status: 200 })
  }) as typeof fetch

  try {
    const products = await loadPostProducts('post/1')
    assert.deepEqual(requests, ['/api/v1/posts/post%2F1'])
    assert.equal(products.length, 1)
    assert.equal(products[0].id, 'official-1')
    assert.equal(products[0].matchType, 'similar')
    assert.equal(products[0].productUrl, 'https://example.com/item')
  } finally {
    globalThis.fetch = previousFetch
  }
})

test('貼文開啟事件使用與商城共用的 session', async () => {
  const previousFetch = globalThis.fetch
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  const values = new Map<string, string>()
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => { values.set(key, value) },
    },
  })
  let sent: Record<string, unknown> | undefined
  globalThis.fetch = (async (_url: string, options: RequestInit) => {
    sent = JSON.parse(String(options.body))[0] as Record<string, unknown>
    return new Response('{}', { status: 200 })
  }) as typeof fetch

  try {
    const session = demoSessionId()
    assert.equal(demoSessionId(), session)
    await recordPostInteraction('post-1', 'post_open')
    assert.equal(sent?.session_id, session)
    assert.equal(sent?.event_type, 'post_open')
    assert.equal(sent?.target_id, 'post-1')
  } finally {
    globalThis.fetch = previousFetch
    if (previousStorage) Object.defineProperty(globalThis, 'localStorage', previousStorage)
    else delete (globalThis as { localStorage?: Storage }).localStorage
  }
})

test('商城搜尋使用共用 session，並把 API 商品映射為可開啟商品卡', async () => {
  const previousFetch = globalThis.fetch
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  const values = new Map<string, string>()
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => { values.set(key, value) },
    },
  })
  let body: Record<string, unknown> | undefined
  globalThis.fetch = (async (_url: string, options: RequestInit) => {
    body = JSON.parse(String(options.body)) as Record<string, unknown>
    return new Response(JSON.stringify({
      products: [{
        score: 0.82,
        explanation: '日系寬鬆風格與你的描述相符。',
        explanation_source: 'llm',
        product: {
          product_id: 'gu-1', name: '寬鬆襯衫', category: 'top', brand: 'GU',
          price: 690, colors: ['black'], product_url: 'https://example.com/gu-1',
        },
      }],
      retrieval: { fusion_method: 'metadata_text', prefilter_count: 1 },
    }), { status: 200 })
  }) as typeof fetch

  try {
    const result = await searchCatalogProducts('寬鬆 襯衫', { category: 'top', priceMax: 1000 })
    assert.equal(body?.session_id, demoSessionId())
    assert.deepEqual(body?.filters, { categories: ['top'], price_max: 1000 })
    assert.equal(body?.mode, 'text')
    assert.equal(body?.query_image, null)
    assert.equal(result.fusionMethod, 'metadata_text')
    assert.equal(result.products[0].id, 'gu-1')
    assert.equal(result.products[0].similarity, 82)
    assert.equal(result.products[0].similarityExplanation, '日系寬鬆風格與你的描述相符。')
    assert.equal(result.products[0].similarityExplanationSource, 'llm')
    assert.equal(result.products[0].productUrl, 'https://example.com/gu-1')
  } finally {
    globalThis.fetch = previousFetch
    if (previousStorage) Object.defineProperty(globalThis, 'localStorage', previousStorage)
    else delete (globalThis as { localStorage?: Storage }).localStorage
  }
})

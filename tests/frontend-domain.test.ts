import test from 'node:test'
import assert from 'node:assert/strict'

import { getMockRecommendation } from '../frontend/src/data/mockRecommendation.ts'

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

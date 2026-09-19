import {
  ArrowUpDown,
  Filter,
  Layers,
  Sparkles,
  X,
} from 'lucide-react'
import { useMemo, useState } from 'react'

import type {
  OutfitItem,
  OutfitItemCategory,
  OutfitPost,
  Product,
} from '../../types/index'

import { ProductItem } from './ProductItem'

interface SimilarProductsProps {
  post?: OutfitPost | null

  sourceItems: OutfitItem[]

  products: Product[]

  isLoading?: boolean

  isDemo?: boolean

  onClose: () => void

  onOpenProduct?: (
    product: Product,
  ) => void
}

const CATEGORY_NAMES: Record<string, string> = {
  all: '全部',
  top: '上衣',
  bottom: '下身',
  outerwear: '外套',
  shoes: '鞋履',
  bag: '包款',
  accessory: '配件',
}

export function SimilarProducts({
  post,
  sourceItems = [],
  products,
  isLoading = false,
  isDemo = false,
  onClose,
  onOpenProduct,
}: SimilarProductsProps) {
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'similarity' | 'priceAsc' | 'priceDesc'>('similarity')

  // Collect available categories from products
  const availableCategories = useMemo(() => {
    const cats = new Set<string>()
    for (const p of products) {
      if (p.category) cats.add(p.category)
    }
    return ['all', ...Array.from(cats)]
  }, [products])

  // Filter and sort products
  const displayedProducts = useMemo(() => {
    let list = activeCategory === 'all'
      ? products
      : products.filter(p => p.category === activeCategory)

    return list.slice().sort((a, b) => {
      if (sortBy === 'priceAsc') return a.price - b.price
      if (sortBy === 'priceDesc') return b.price - a.price
      return (b.similarity ?? 0) - (a.similarity ?? 0)
    })
  }, [products, activeCategory, sortBy])

  return (
    <>
      <button
        type="button"
        className="drawer-backdrop"
        aria-label="關閉商品"
        onClick={onClose}
      />

      <aside className="product-drawer">
        <header>
          <div>
            <span className="drawer-subtitle">
              <Sparkles size={13} className="sparkle-icon" />
              SHOP THE LOOK
            </span>

            <h2>
              貼文商品與搭配推薦
            </h2>
          </div>

          <button
            type="button"
            className="close-button"
            aria-label="關閉"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>

        {/* Outfit Preview Header (if post provided) */}
        {post && (
          <div className="drawer-outfit-hero">
            {post.imageUrl && (
              <img
                src={post.imageUrl}
                alt={post.caption}
                className="drawer-outfit-thumb"
              />
            )}
            <div className="drawer-outfit-meta">
              <h4>{post.outfit?.name || post.caption}</h4>
              <p>@{post.author.username} 的風格穿搭</p>
              {post.outfit?.styles && (
                <div className="drawer-style-tags">
                  {post.outfit.styles.map(s => (
                    <span key={s} className="drawer-style-pill">#{s}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="product-source">
          <strong>
            {sourceItems.length > 0 ? (
              <>穿搭標籤： {sourceItems.length} 個單品</>
            ) : (
              <>AI 視覺檢索：</>
            )}
          </strong>

          <span>
            {sourceItems.length > 0
              ? sourceItems.map(item => item.name).join(' · ')
              : (post?.outfit?.name || post?.caption || '精選單品搭配')}
          </span>
          <small>
            {isDemo
              ? '✨ 依據貼文風格智慧推薦相襯的高契合單品'
              : '以貼文圖片透過 FashionCLIP 找到的相似商品；非創作者同款'}
          </small>
        </div>

        {/* Category Filter Chips & Sort Controls */}
        {!isLoading && products.length > 0 && (
          <div className="similar-products-controls">
            <div className="category-chips-scroll">
              {availableCategories.map(cat => {
                const count = cat === 'all'
                  ? products.length
                  : products.filter(p => p.category === cat).length
                return (
                  <button
                    key={cat}
                    type="button"
                    className={`category-chip-btn ${activeCategory === cat ? 'active' : ''}`}
                    onClick={() => setActiveCategory(cat)}
                  >
                    <span>{CATEGORY_NAMES[cat] ?? cat}</span>
                    <span className="chip-count">{count}</span>
                  </button>
                )
              })}
            </div>

            <div className="sort-selector-row">
              <span className="sort-label">
                <ArrowUpDown size={12} />
                排序：
              </span>
              <select
                className="sort-dropdown"
                value={sortBy}
                onChange={e => setSortBy(e.target.value as any)}
              >
                <option value="similarity">最高相似度</option>
                <option value="priceAsc">價格：由低到高</option>
                <option value="priceDesc">價格：由高到低</option>
              </select>
            </div>
          </div>
        )}

        <div className="product-list">
          {isLoading ? (
            <div className="empty-state" role="status">
              <div className="loading-spinner" />
              <p>正在透過 FashionCLIP 搜尋相似單品…</p>
            </div>
          ) : displayedProducts.length ? (
            displayedProducts.map(product => (
              <ProductItem
                key={product.id}
                product={product}
                onOpenProduct={onOpenProduct}
              />
            ))
          ) : (
            <div className="empty-state">
              <h2>
                此類別暫無單品
              </h2>
              <p>
                目前類別「{CATEGORY_NAMES[activeCategory] ?? activeCategory}」沒有篩選結果。
              </p>
              <button
                type="button"
                className="reset-category-btn"
                onClick={() => setActiveCategory('all')}
              >
                查看全部 ({products.length}) 件單品
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}

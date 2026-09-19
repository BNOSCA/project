import {
  Bookmark,
  Check,
  Copy,
  ExternalLink,
  Footprints,
  ShoppingBag,
  Shirt,
  Sparkles,
} from 'lucide-react'
import { useEffect, useState } from 'react'

import type {
  Product,
} from '../../types/index'

interface ProductItemProps {
  product: Product

  onOpenProduct?: (
    product: Product,
  ) => void
}

function ProductImageFallback({ category }: { category: Product['category'] }) {
  const Icon = category === 'shoes' ? Footprints : category === 'top' || category === 'outerwear'
    ? Shirt : ShoppingBag
  return (
    <div className="product-image-fallback" aria-label={`${category} 商品圖片暫時無法載入`}>
      <Icon size={31} strokeWidth={1.4} />
      <span>{category}</span>
    </div>
  )
}

export function ProductItem({
  product,
  onOpenProduct,
}: ProductItemProps) {
  const [imageFailed, setImageFailed] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  const [isCopied, setIsCopied] = useState(false)

  useEffect(() => setImageFailed(false), [product.imageUrl])

  function handleToggleSave(e: React.MouseEvent) {
    e.stopPropagation()
    setIsSaved(prev => !prev)
  }

  async function handleCopyName(e: React.MouseEvent) {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(`${product.brand} ${product.name}`)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    } catch {
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    }
  }

  return (
    <article className="product-card interactive-product-card">
      <div
        className="product-image"
        style={{
          backgroundColor: product.color,
        }}
        onClick={() => onOpenProduct?.(product)}
      >
        {product.imageUrl && !imageFailed ? (
          <img
            src={product.imageUrl}
            alt={product.name}
            loading="lazy"
            onError={() => setImageFailed(true)}
            className="product-actual-img"
          />
        ) : (
          <ProductImageFallback category={product.category} />
        )}

        {/* Quick Wishlist / Save Button on Image */}
        <button
          type="button"
          className={`product-quick-save ${isSaved ? 'active' : ''}`}
          onClick={handleToggleSave}
          title={isSaved ? '從願望清單移除' : '加入願望清單'}
          aria-label="收藏商品"
        >
          <Bookmark size={14} fill={isSaved ? 'currentColor' : 'none'} />
        </button>

        {/* Visual Similarity Badge */}
        {typeof product.similarity === 'number' && (
          <div className="product-similarity-pill">
            <Sparkles size={11} />
            <span>{product.similarity}% 相似</span>
          </div>
        )}
      </div>

      <div className="product-info">
        <div className="product-brand-row">
          <span className="product-brand-tag">
            {product.brand}
          </span>
          {product.matchType && (
            <span className={`product-match-badge ${product.matchType}`}>
              {product.matchType === 'exact' ? '同款' : '視覺相似'}
            </span>
          )}
        </div>

        <strong
          className="product-title-clickable"
          onClick={() => onOpenProduct?.(product)}
          title={product.name}
        >
          {product.name}
        </strong>

        <div className="product-footer-row">
          <div className="product-price-block">
            <span className="product-currency">NT$</span>
            <b className="product-price-num">
              {product.price.toLocaleString()}
            </b>
          </div>

          <div className="product-action-btns">
            <button
              type="button"
              className={`product-copy-btn ${isCopied ? 'copied' : ''}`}
              onClick={handleCopyName}
              title="複製商品名稱"
            >
              {isCopied ? <Check size={12} /> : <Copy size={12} />}
              <span>{isCopied ? '已複製' : '品名'}</span>
            </button>

            <button
              type="button"
              className="product-view-btn"
              onClick={() => onOpenProduct?.(product)}
            >
              查看
              <ExternalLink size={11} />
            </button>
          </div>
        </div>
      </div>
    </article>
  )
}

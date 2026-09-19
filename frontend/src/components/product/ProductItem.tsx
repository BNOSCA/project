import {
  ExternalLink,
  Footprints,
  ShoppingBag,
  Shirt,
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
  useEffect(() => setImageFailed(false), [product.imageUrl])
  return (
    <article className="product-card">
      <div
        className="product-image"
        style={{
          backgroundColor:
            product.color,
        }}
      >
        {product.imageUrl && !imageFailed ? (
          <img src={product.imageUrl} alt={product.name} loading="lazy"
            onError={() => setImageFailed(true)} />
        ) : (
          <ProductImageFallback category={product.category} />
        )}
      </div>

      <div className="product-info">
        <span>
          {product.brand}
        </span>

        <strong>
          {product.name}
        </strong>

        {product.matchType && (
          <small>{product.matchType === 'exact' ? '同款' : '視覺近似商品（非同款）'}</small>
        )}

        {typeof product.similarity ===
          'number' && (
          <small>
            搜尋相關分數 ·
            {' '}
            {product.similarity}/100
          </small>
        )}

        <div>
          <b>
            NT$
            {' '}
            {product.price.toLocaleString()}
          </b>

          <button
            type="button"
            onClick={() =>
              onOpenProduct?.(
                product,
              )
            }
          >
            查看
            {' '}
            <ExternalLink
              size={11}
            />
          </button>
        </div>
      </div>
    </article>
  )
}

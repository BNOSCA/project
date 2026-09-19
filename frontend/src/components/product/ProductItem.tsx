import {
  ExternalLink,
} from 'lucide-react'
import { useState } from 'react'

import type {
  Product,
} from '../../types/index'

interface ProductItemProps {
  product: Product

  onOpenProduct?: (
    product: Product,
  ) => void
}

export function ProductItem({
  product,
  onOpenProduct,
}: ProductItemProps) {
  const [imageFailed, setImageFailed] = useState(false)
  return (
    <article className="product-card">
      <div
        className="product-image"
        style={{
          backgroundColor:
            product.color,
        }}
      >
        {product.imageUrl && !imageFailed && (
          <img src={product.imageUrl} alt={product.name} loading="lazy"
            onError={() => setImageFailed(true)} />
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
          <small>{product.matchType === 'exact' ? '同款' : '相似商品（展示配對）'}</small>
        )}

        {typeof product.similarity ===
          'number' && (
          <small>
            與這套相似 ·
            {' '}
            {product.similarity}%
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

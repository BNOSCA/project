import {
  ExternalLink,
} from 'lucide-react'

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
  return (
    <article className="product-card">
      <div
        className="product-image"
        style={{
          backgroundColor:
            product.color,
        }}
      />

      <div className="product-info">
        <span>
          {product.brand}
        </span>

        <strong>
          {product.name}
        </strong>

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
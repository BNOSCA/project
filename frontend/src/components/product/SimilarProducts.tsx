import {
  X,
} from 'lucide-react'

import type {
  OutfitItem,
  Product,
} from '../../types/index'

import { ProductItem } from './ProductItem'

interface SimilarProductsProps {
  sourceItems: OutfitItem[]

  products: Product[]

  onClose: () => void

  onOpenProduct?: (
    product: Product,
  ) => void
}

export function SimilarProducts({
  sourceItems,
  products,
  onClose,
  onOpenProduct,
}: SimilarProductsProps) {
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
            <span>
              SHOP THE LOOK
            </span>

            <h2>
              找到相似單品
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

        <div className="product-source">
          <strong>
            AI 辨識到
            {' '}
            {sourceItems.length}
            {' '}
            個主要單品
          </strong>

          <span>
            {sourceItems
              .map(
                item =>
                  item.name,
              )
              .join(' · ')}
          </span>
        </div>

        <div className="product-list">
          {products.length ? (
            products.map(product => (
              <ProductItem
                key={product.id}
                product={product}
                onOpenProduct={
                  onOpenProduct
                }
              />
            ))
          ) : (
            <div className="empty-state">
              <h2>
                暫時沒有相似商品
              </h2>

              <p>
                商品資料庫之後會持續擴充。
              </p>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
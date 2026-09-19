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

  isLoading?: boolean

  isDemo?: boolean

  onClose: () => void

  onOpenProduct?: (
    product: Product,
  ) => void
}

export function SimilarProducts({
  sourceItems,
  products,
  isLoading = false,
  isDemo = false,
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
              貼文商品
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
            穿搭標籤：
            {' '}
            {sourceItems.length}
            {' '}
            個單品
          </strong>

          <span>
            {sourceItems
              .map(
                item =>
                  item.name,
              )
              .join(' · ')}
          </span>
          <small>{isDemo
            ? '本機示範商品'
            : '以貼文圖片透過 FashionCLIP 找到的相似商品；非創作者同款'}</small>
        </div>

        <div className="product-list">
          {isLoading ? (
            <div className="empty-state" role="status">正在載入商品…</div>
          ) : products.length ? (
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
                這張貼文目前沒有達到相似門檻的有圖商品。
              </p>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}

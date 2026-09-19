import {
  Search,
} from 'lucide-react'
import {
  useState,
} from 'react'
import type {
  FormEvent,
} from 'react'

import { ProductItem } from '../components/product/ProductItem'
import {
  searchCatalogProducts,
} from '../services/feed'
import type {
  Product,
} from '../types'

interface ShopPageProps {
  onOpenProduct: (product: Product) => void
}

const categories = [
  { value: '', label: '全部類別' },
  { value: 'top', label: '上衣' },
  { value: 'bottom', label: '下身' },
  { value: 'shoes', label: '鞋款' },
  { value: 'outerwear', label: '外套' },
  { value: 'accessory', label: '配件' },
]

export function ShopPage({
  onOpenProduct,
}: ShopPageProps) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [priceMax, setPriceMax] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [method, setMethod] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!query.trim() || isLoading) return
    setIsLoading(true)
    setError('')
    try {
      const result = await searchCatalogProducts(query.trim(), {
        category: category || undefined,
        priceMax: priceMax ? Number(priceMax) : undefined,
      })
      setProducts(result.products)
      setMethod(result.fusionMethod)
    } catch (searchError) {
      setProducts([])
      setMethod('')
      setError(searchError instanceof Error ? searchError.message : '目前無法搜尋商品。')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="page-section shop-page">
      <div className="section-heading">
        <div>
          <span className="eyebrow">SHOP</span>
          <h1>找可購買的單品。</h1>
          <p>先套用類別與價格限制，再依文字相關性排序。</p>
        </div>
      </div>

      <form className="shop-search-form" onSubmit={submit}>
        <div className="search-box">
          <Search size={19} />
          <input
            type="search"
            value={query}
            placeholder="例如：日系 寬鬆 襯衫"
            aria-label="搜尋商品"
            onChange={event => setQuery(event.target.value)}
          />
        </div>
        <div className="shop-filters">
          <select value={category} aria-label="商品類別" onChange={event => setCategory(event.target.value)}>
            {categories.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
          <select value={priceMax} aria-label="最高價格" onChange={event => setPriceMax(event.target.value)}>
            <option value="">不限價格</option>
            <option value="1000">NT$1,000 以下</option>
            <option value="2000">NT$2,000 以下</option>
            <option value="3000">NT$3,000 以下</option>
          </select>
          <button type="submit" disabled={!query.trim() || isLoading}>
            {isLoading ? '搜尋中…' : '搜尋'}
          </button>
        </div>
      </form>

      {error && <div className="recommendation-error" role="alert">{error}</div>}
      {method && <p className="shop-method">排序方式：{method === 'metadata_text' ? '文字欄位比對' : method}</p>}
      {products.length > 0 && (
        <div className="shop-product-list">
          {products.map(product => (
            <ProductItem key={product.id} product={product} onOpenProduct={onOpenProduct} />
          ))}
        </div>
      )}
      {!isLoading && !error && query && products.length === 0 && method && (
        <div className="empty-state">
          <h2>沒有符合條件的可購買商品</h2>
          <p>可調整文字、類別或價格限制後再試。</p>
        </div>
      )}
    </section>
  )
}

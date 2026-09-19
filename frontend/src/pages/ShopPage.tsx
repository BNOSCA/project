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

const colors = [
  { value: 'black', label: '黑色' },
  { value: 'white', label: '白色' },
  { value: 'beige', label: '米色' },
  { value: 'charcoal', label: '深灰色' },
  { value: 'blue', label: '藍色' },
]

const fits = [
  { value: 'slim', label: '合身' },
  { value: 'relaxed', label: '寬鬆' },
  { value: 'regular', label: '標準' },
]

const sizes = ['XS', 'S', 'M', 'L', 'XL']

export function ShopPage({
  onOpenProduct,
}: ShopPageProps) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [priceMax, setPriceMax] = useState('')
  const [excludedColor, setExcludedColor] = useState('')
  const [excludedFit, setExcludedFit] = useState('')
  const [size, setSize] = useState('')
  const [availableOnly, setAvailableOnly] = useState(false)
  const [products, setProducts] = useState<Product[]>([])
  const [method, setMethod] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const hasFilter = Boolean(category || priceMax || excludedColor || excludedFit || size || availableOnly)
    if ((!query.trim() && !hasFilter) || isLoading) return
    setIsLoading(true)
    setError('')
    try {
      const result = await searchCatalogProducts({
        queryText: query,
        filters: {
          category: category || undefined,
          priceMax: priceMax ? Number(priceMax) : undefined,
          availableOnly,
          excludedColors: excludedColor ? [excludedColor] : [],
          excludedFits: excludedFit ? [excludedFit] : [],
          sizes: size ? [size] : [],
        },
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
          <p>先套用條件，再用 FashionCLIP 排序；也可只用條件瀏覽。</p>
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
          <select value={size} aria-label="尺寸" onChange={event => setSize(event.target.value)}>
            <option value="">不限尺寸</option>
            {sizes.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
          <button type="submit" disabled={(!query.trim() && !category && !priceMax && !excludedColor && !excludedFit && !size && !availableOnly) || isLoading}>
            {isLoading ? '搜尋中…' : '搜尋'}
          </button>
        </div>
        <div className="shop-filters shop-advanced-filters">
          <select value={excludedColor} aria-label="排除顏色" onChange={event => setExcludedColor(event.target.value)}>
            <option value="">不排除顏色</option>
            {colors.map(item => <option key={item.value} value={item.value}>排除{item.label}</option>)}
          </select>
          <select value={excludedFit} aria-label="排除版型" onChange={event => setExcludedFit(event.target.value)}>
            <option value="">不排除版型</option>
            {fits.map(item => <option key={item.value} value={item.value}>排除{item.label}</option>)}
          </select>
          <label className="shop-checkbox">
            <input type="checkbox" checked={availableOnly}
              onChange={event => setAvailableOnly(event.target.checked)} />
            僅顯示有庫存
          </label>
        </div>
      </form>

      {error && <div className="recommendation-error" role="alert">{error}</div>}
      {method && <p className="shop-method">排序方式：{describeMethod(method)}</p>}
      {products.length > 0 && (
        <div className="shop-product-list">
          {products.map(product => (
            <ProductItem key={product.id} product={product} onOpenProduct={onOpenProduct} />
          ))}
        </div>
      )}
      {!isLoading && !error && products.length === 0 && method && (
        <div className="empty-state">
          <h2>沒有符合條件的可購買商品</h2>
          <p>可調整文字、類別或價格限制後再試。</p>
        </div>
      )}
    </section>
  )
}

function describeMethod(method: string) {
  return {
    fashion_clip_text: 'FashionCLIP 文字語意相似度',
    fashion_clip_image: 'FashionCLIP 圖像視覺相似度',
    rrf: '文字與圖片的 RRF 排名融合',
    metadata_text: '文字欄位比對（FashionCLIP 暫時不可用）',
    embedding_unavailable_image: '圖片相似度暫時不可用',
    filters_only: '依篩選條件瀏覽',
  }[method] ?? method
}

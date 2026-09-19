import { ImagePlus, RefreshCw } from 'lucide-react'
import { useRef, useState } from 'react'

import { Avatar } from '../components/common/Avatar'
import { OutfitPost } from '../components/post/OutfitPost'
import { ProductItem } from '../components/product/ProductItem'
import { AIQueryBar } from '../components/search/AIQueryBar'
import type { CatalogSearchResult } from '../services/feed'

import type {
  OutfitPost as OutfitPostModel,
  Product,
  User,
} from '../types/index'

type FeedMode =
  | 'for-you'
  | 'following'

interface HomePageProps {
  currentUser: User

  posts: OutfitPostModel[]

  likedIds: string[]
  savedIds: string[]

  onLike: (
    postId: string,
  ) => void

  onSave: (
    postId: string,
  ) => void

  onFindProducts: (
    post: OutfitPostModel,
  ) => void

  onCreatePost: () => void

  onRefreshFeed: () => Promise<void>
  onImpression: (postId: string, position: number) => void
  onOpenProduct: (product: Product) => void
  onShare?: (post: OutfitPostModel) => void
}

export function HomePage({
  currentUser,
  posts,
  likedIds,
  savedIds,
  onLike,
  onSave,
  onFindProducts,
  onCreatePost,
  onRefreshFeed,
  onImpression,
  onOpenProduct,
  onShare,
}: HomePageProps) {
  const [
    feedMode,
    setFeedMode,
  ] = useState<FeedMode>(
    'for-you',
  )

  const [searchResult, setSearchResult] =
    useState<CatalogSearchResult | null>(null)
  const [searchError, setSearchError] =
    useState('')
  const [isSearching, setIsSearching] =
    useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)
  const touchStartY = useRef<number | null>(null)

  async function refresh() {
    if (isRefreshing) return
    setIsRefreshing(true)
    try {
      await onRefreshFeed()
    } finally {
      setIsRefreshing(false)
      setPullDistance(0)
    }
  }

  /*
   * Demo 階段：
   * 暫時以部分貼文模擬「追蹤中」。
   *
   * 後續串 Supabase 後會改成：
   *
   * follows
   *   ↓
   * followed user ids
   *   ↓
   * posts query
   */
  const visiblePosts =
    feedMode === 'for-you'
      ? posts
      : posts.filter(
          (_, index) =>
            index % 2 === 0,
        )

  return (
    <div
      className="home-page"
      onTouchStart={event => {
        if (window.scrollY <= 0) touchStartY.current = event.touches[0]?.clientY ?? null
      }}
      onTouchMove={event => {
        if (touchStartY.current === null) return
        setPullDistance(Math.min(72, Math.max(0, (event.touches[0]?.clientY ?? 0) - touchStartY.current)))
      }}
      onTouchEnd={() => {
        touchStartY.current = null
        if (pullDistance >= 56) void refresh()
        else setPullDistance(0)
      }}
    >
      <div className={`pull-refresh ${isRefreshing ? 'refreshing' : ''}`} style={{ height: pullDistance }} aria-hidden="true">
        <RefreshCw size={18} />
      </div>
      <header className="feed-tabs">
        <button
          type="button"
          className={
            feedMode === 'for-you'
              ? 'active'
              : ''
          }
          onClick={() =>
            setFeedMode(
              'for-you',
            )
          }
        >
          為你推薦
        </button>

        <button
          type="button"
          className={
            feedMode === 'following'
              ? 'active'
              : ''
          }
          onClick={() =>
            setFeedMode(
              'following',
            )
          }
        >
          追蹤中
        </button>
      </header>

      <section className="home-ai-section">
        <AIQueryBar
          isLoading={isSearching}
          onStart={() => {
            setIsSearching(true)
            setSearchError('')
            setSearchResult(null)
          }}
          onResult={response => {
            setSearchResult(response)
            setIsSearching(false)
            void onRefreshFeed().catch(() => {
              setSearchError('商品結果已更新，但貼文推薦暫時無法刷新。')
            })
          }}
          onError={message => {
            setSearchError(message)
            setIsSearching(false)
          }}
        />

        {isSearching && <SearchResultSkeleton />}
        {searchError && (
          <div className="recommendation-error" role="alert">
            {searchError}
          </div>
        )}
        {searchResult && (
          <section className="home-search-results" aria-live="polite">
            <div className="recommendation-heading-row">
              <h2>相似商品</h2>
              <span>{searchResult.products.length} 件結果</span>
            </div>
            <p className="search-result-method">
              {describeSearchMethod(searchResult.fusionMethod, searchResult.candidateCount)}
            </p>
            {searchResult.products.length > 0 ? (
              <div className="shop-product-list">
                {searchResult.products.map(product => (
                  <ProductItem key={product.id} product={product} onOpenProduct={onOpenProduct} />
                ))}
              </div>
            ) : (
              <div className="recommendation-empty">
                <strong>找不到相似商品</strong>
                <p>試試調整描述，或改用更清楚的參考圖片。</p>
              </div>
            )}
          </section>
        )}
      </section>

      <section className="quick-post">
        <Avatar
          user={currentUser}
          size="small"
        />

        <button
          type="button"
          onClick={onCreatePost}
        >
          分享今天的穿搭...
        </button>

        <button
          type="button"
          className="quick-post-icon"
          aria-label="新增穿搭貼文"
          onClick={onCreatePost}
        >
          <ImagePlus
            size={20}
          />
        </button>
      </section>

      <div className="feed-section-label">
        <div>
          <span>FOR YOU</span>
          <h2>穿搭靈感</h2>
        </div>
        <button className="feed-refresh-button" type="button" onClick={() => void refresh()} disabled={isRefreshing} aria-label="更新推薦貼文" title="更新推薦貼文">
          <RefreshCw size={17} />
        </button>
      </div>

      <section className="feed">
        {visiblePosts.length === 0 && (
          <div className="empty-state">
            <h2>目前沒有穿搭貼文</h2>
            <p>請稍後重新整理，或切回「為你推薦」。</p>
          </div>
        )}
        {visiblePosts.map(
          (post, index) => (
            <OutfitPost
              key={post.id}
              post={post}
              liked={likedIds.includes(
                post.id,
              )}
              saved={savedIds.includes(
                post.id,
              )}
              onLike={onLike}
              onSave={onSave}
              onFindProducts={
                onFindProducts
              }
              onShare={onShare ? () => onShare(post) : undefined}
              onImpression={postId => onImpression(postId, index)}
            />
          ),
        )}
      </section>
    </div>
  )
}

function describeSearchMethod(method: string, candidateCount: number) {
  const source = {
    fashion_clip_text: 'FashionCLIP 文字語意相似度',
    fashion_clip_text_image: 'FashionCLIP 文字與商品圖片融合排序',
    fashion_clip_image: 'FashionCLIP 圖像視覺相似度',
    rrf: '文字與圖片的 RRF 排名融合',
    metadata_text: '文字欄位比對（FashionCLIP 暫時不可用）',
    embedding_unavailable_image: '圖片相似度暫時不可用',
    filters_only: '依條件篩選',
  }[method] ?? method
  return `${source} · 在 ${candidateCount} 件符合條件的商品中排序`
}

function SearchResultSkeleton() {
  return (
    <section className="recommendation-section" aria-busy="true">
      <div className="recommendation-title"><span>正在搜尋相似商品…</span></div>
      <div className="recommendation-skeleton"><div /><span /><span /></div>
    </section>
  )
}

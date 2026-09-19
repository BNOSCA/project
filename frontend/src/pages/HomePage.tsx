import { ImagePlus, RefreshCw } from 'lucide-react'
import { useRef, useState } from 'react'

import { Avatar } from '../components/common/Avatar'
import { OutfitPost } from '../components/post/OutfitPost'
import { AIQueryBar } from '../components/search/AIQueryBar'
import {
  RecommendationResults,
  RecommendationSkeleton,
} from '../components/search/RecommendationResults'

import type { RecommendResponse } from '../services/recommendation'

import type {
  OutfitPost as OutfitPostModel,
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
}: HomePageProps) {
  const [
    feedMode,
    setFeedMode,
  ] = useState<FeedMode>(
    'for-you',
  )

  const [recommendation, setRecommendation] =
    useState<RecommendResponse | null>(null)
  const [recommendationError, setRecommendationError] =
    useState('')
  const [isRecommending, setIsRecommending] =
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
          isLoading={isRecommending}
          onStart={() => {
            setIsRecommending(true)
            setRecommendationError('')
            setRecommendation(null)
          }}
          onResult={response => {
            setRecommendation(response)
            setIsRecommending(false)
            void onRefreshFeed()
          }}
          onError={message => {
            setRecommendationError(message)
            setIsRecommending(false)
          }}
        />

        {isRecommending && <RecommendationSkeleton />}
        {recommendationError && (
          <div className="recommendation-error" role="alert">
            {recommendationError}
          </div>
        )}
        {recommendation && (
          <RecommendationResults response={recommendation} />
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
              onImpression={postId => onImpression(postId, index)}
            />
          ),
        )}
      </section>
    </div>
  )
}

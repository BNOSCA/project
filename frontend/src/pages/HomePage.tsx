import { ImagePlus } from 'lucide-react'
import { useState } from 'react'

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
    <>
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
        <p>來自社群的最新搭配</p>
      </div>

      <section className="feed">
        {visiblePosts.map(
          post => (
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
            />
          ),
        )}
      </section>
    </>
  )
}

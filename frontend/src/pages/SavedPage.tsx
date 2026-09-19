import {
  Bookmark,
} from 'lucide-react'

import { OutfitPost } from '../components/post/OutfitPost'

import type {
  OutfitPost as OutfitPostModel,
} from '../types/index'

interface SavedPageProps {
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

  onGoHome: () => void

  onShare?: (
    post: OutfitPostModel,
  ) => void
}

export function SavedPage({
  posts,
  likedIds,
  savedIds,
  onLike,
  onSave,
  onFindProducts,
  onGoHome,
  onShare,
}: SavedPageProps) {
  const savedPosts =
    posts.filter(post =>
      savedIds.includes(
        post.id,
      ),
    )

  return (
    <section className="page-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">
            SAVED
          </span>

          <h1>
            收藏的穿搭。
          </h1>

          <p>
            收藏同時也是個人化推薦的重要訊號。
          </p>
        </div>
      </div>

      {savedPosts.length >
      0 ? (
        <div className="discover-grid">
          {savedPosts.map(
            post => (
              <OutfitPost
                key={post.id}
                variant="grid"
                post={post}
                liked={likedIds.includes(
                  post.id,
                )}
                saved
                onLike={onLike}
                onSave={onSave}
                onFindProducts={
                  onFindProducts
                }
                onShare={onShare ? () => onShare(post) : undefined}
              />
            ),
          )}
        </div>
      ) : (
        <div className="empty-state">
          <Bookmark
            size={30}
            strokeWidth={1.4}
          />

          <h2>
            還沒有收藏
          </h2>

          <p>
            看到喜歡的穿搭，
            按下書籤就會出現在這裡。
          </p>

          <button
            type="button"
            className="secondary-button"
            onClick={onGoHome}
          >
            去逛逛
          </button>
        </div>
      )}
    </section>
  )
}
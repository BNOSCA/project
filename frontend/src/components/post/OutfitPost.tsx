import {
  ShoppingBag,
} from 'lucide-react'
import { useEffect, useRef } from 'react'

import type {
  OutfitPost as OutfitPostModel,
} from '../../types/index'

import { OutfitVisual } from './OutfitVisual'
import { PostActions } from './PostActions'
import { PostHeader } from './PostHeader'

interface OutfitPostProps {
  post: OutfitPostModel

  liked: boolean
  saved: boolean

  variant?: 'feed' | 'grid'

  onLike: (
    postId: string,
  ) => void

  onSave: (
    postId: string,
  ) => void

  onFindProducts: (
    post: OutfitPostModel,
  ) => void

  onComment?: (
    postId: string,
  ) => void

  onShare?: (
    postId: string,
  ) => void

  onImpression?: (postId: string) => void
}

export function OutfitPost({
  post,
  liked,
  saved,
  variant = 'feed',
  onLike,
  onSave,
  onFindProducts,
  onComment,
  onShare,
  onImpression,
}: OutfitPostProps) {
  const articleRef = useRef<HTMLElement>(null)
  const impressionSent = useRef(false)

  useEffect(() => {
    if (!onImpression || variant !== 'feed' || !articleRef.current) return
    const element = articleRef.current
    const observer = new IntersectionObserver(entries => {
      if (!impressionSent.current && entries.some(entry => entry.isIntersecting && entry.intersectionRatio >= 0.6)) {
        impressionSent.current = true
        onImpression(post.id)
        observer.disconnect()
      }
    }, { threshold: 0.6 })
    observer.observe(element)
    return () => observer.disconnect()
  }, [onImpression, post.id, variant])
  const visibleLikeCount =
    post.stats.likeCount +
    (
      liked &&
      !post.viewerState.liked
        ? 1
        : 0
    )

  return (
    <article
      ref={articleRef}
      className={
        variant === 'grid'
          ? 'social-post grid-post'
          : 'social-post'
      }
    >
      <PostHeader
        author={post.author}
        createdAt={post.createdAt}
      />

      <OutfitVisual
        outfit={post.outfit}
        imageUrl={post.imageUrl}
        matchScore={post.matchScore}
      />

      <PostActions
        liked={liked}
        saved={saved}
        onLike={() =>
          onLike(post.id)
        }
        onSave={() =>
          onSave(post.id)
        }
        onComment={
          onComment
            ? () =>
                onComment(post.id)
            : undefined
        }
        onShare={
          onShare
            ? () =>
                onShare(post.id)
            : undefined
        }
      />

      <div className="post-copy">
        <strong>
          {visibleLikeCount.toLocaleString()}
          {' '}
          個讚
        </strong>

        <p>
          <b>
            @{post.author.username}
          </b>
          {' '}
          {post.caption}
        </p>

        <div className="post-tags">
          {post.outfit.styles
            .slice(0, 2)
            .map(style => (
              <button
                key={style}
                type="button"
              >
                #
                {style.replace(
                  /\s+/g,
                  '',
                )}
              </button>
            ))}

          {post.outfit.occasions
            .slice(0, 1)
            .map(occasion => (
              <button
                key={occasion}
                type="button"
              >
                #
                {occasion.replace(
                  /\s+/g,
                  '',
                )}
              </button>
            ))}
        </div>

        <button
          type="button"
          className="comments-preview"
          onClick={
            onComment
              ? () =>
                  onComment(post.id)
              : undefined
          }
        >
          查看全部
          {' '}
          {post.stats.commentCount}
          {' '}
          則留言
        </button>
      </div>

      <button
        type="button"
        className="shop-look-button"
        onClick={() =>
          onFindProducts(post)
        }
      >
        <span>
          <ShoppingBag
            size={18}
          />

          <span>
            <strong>
              找這套的相似商品
            </strong>

            <small>
              {post.outfit.items.length}
              {' '}
              items
            </small>
          </span>
        </span>

        <span>
          查看
        </span>
      </button>
    </article>
  )
}

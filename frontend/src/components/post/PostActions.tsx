import {
  Bookmark,
  Heart,
  MessageCircle,
  Send,
} from 'lucide-react'

interface PostActionsProps {
  liked: boolean
  saved: boolean

  onLike: () => void
  onSave: () => void

  onComment?: () => void
  onShare?: () => void
}

export function PostActions({
  liked,
  saved,
  onLike,
  onSave,
  onComment,
  onShare,
}: PostActionsProps) {
  return (
    <div className="post-actions">
      <div>
        <button
          type="button"
          className={
            liked
              ? 'interaction active-like'
              : 'interaction'
          }
          aria-label={
            liked
              ? '取消喜歡'
              : '喜歡'
          }
          aria-pressed={liked}
          onClick={onLike}
        >
          <Heart
            size={23}
            fill={
              liked
                ? 'currentColor'
                : 'none'
            }
          />
        </button>

        <button
          type="button"
          className="interaction"
          aria-label="留言"
          onClick={onComment}
        >
          <MessageCircle size={23} />
        </button>

        <button
          type="button"
          className="interaction"
          aria-label="分享"
          onClick={onShare}
        >
          <Send size={22} />
        </button>
      </div>

      <button
        type="button"
        className={
          saved
            ? 'interaction saved'
            : 'interaction'
        }
        aria-label={
          saved
            ? '取消收藏'
            : '收藏'
        }
        aria-pressed={saved}
        onClick={onSave}
      >
        <Bookmark
          size={23}
          fill={
            saved
              ? 'currentColor'
              : 'none'
          }
        />
      </button>
    </div>
  )
}
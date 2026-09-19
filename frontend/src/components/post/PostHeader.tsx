import {
  MoreHorizontal,
} from 'lucide-react'

import type { User } from '../../types/index'

import { Avatar } from '../common/Avatar'

interface PostHeaderProps {
  author: User

  createdAt: string
}

function formatRelativeTime(
  createdAt: string,
) {
  const created = new Date(createdAt)

  const now = new Date()

  const diff =
    now.getTime() - created.getTime()

  const hours =
    Math.floor(
      diff / (1000 * 60 * 60),
    )

  if (hours < 1) {
    return '剛剛'
  }

  if (hours < 24) {
    return `${hours}h`
  }

  const days =
    Math.floor(hours / 24)

  return `${days}d`
}

export function PostHeader({
  author,
  createdAt,
}: PostHeaderProps) {
  return (
    <header className="post-header">
      <div className="post-author">
        <Avatar
          user={author}
          size="small"
        />

        <div>
          <strong>
            {author.displayName}
          </strong>

          <span>
            @{author.username}
            {' · '}
            {formatRelativeTime(createdAt)}
          </span>
        </div>
      </div>

      <button
        type="button"
        className="plain-icon-button"
        aria-label="更多"
      >
        <MoreHorizontal size={21} />
      </button>
    </header>
  )
}
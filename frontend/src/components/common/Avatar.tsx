import type { User } from '../../types/index'

interface AvatarProps {
  user: User

  size?: 'small' | 'medium' | 'large'

  className?: string
}

export function Avatar({
  user,
  size = 'medium',
  className = '',
}: AvatarProps) {
  const sizeClass =
    size === 'small'
      ? 'avatar-small'
      : size === 'large'
        ? 'avatar-large'
        : ''

  if (user.avatarUrl) {
    return (
      <img
        className={`avatar ${sizeClass} ${className}`}
        src={user.avatarUrl}
        alt={`${user.displayName} avatar`}
      />
    )
  }

  return (
    <span
      className={`avatar ${sizeClass} ${className}`}
      aria-label={user.displayName}
    >
      {user.avatarText}
    </span>
  )
}
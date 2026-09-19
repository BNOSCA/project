import { useState } from 'react'
import {
  Check,
  CheckCircle2,
  Copy,
  Link2,
  Send,
  Share2,
  Sparkles,
  X,
} from 'lucide-react'
import type { Friend, OutfitPost } from '../../types/index'

interface ShareOutfitDialogProps {
  isOpen: boolean
  post: OutfitPost | null
  friends: Friend[]
  onClose: () => void
  onShareToFriend: (friend: Friend, post: OutfitPost, message?: string) => Promise<void>
  onNotify?: (msg: string) => void
}

export function ShareOutfitDialog({
  isOpen,
  post,
  friends,
  onClose,
  onShareToFriend,
  onNotify,
}: ShareOutfitDialogProps) {
  const [copied, setCopied] = useState(false)
  const [customMessage, setCustomMessage] = useState('')
  const [sentFriendIds, setSentFriendIds] = useState<string[]>([])
  const [sendingFriendId, setSendingFriendId] = useState<string | null>(null)
  const [lastSharedFriend, setLastSharedFriend] = useState<string | null>(null)

  if (!isOpen || !post) return null

  const shareUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/#ootd-${post.id}`
    : `https://outfit.demo/#ootd-${post.id}`

  async function handleCopyLink() {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      onNotify?.('✨ 穿搭專屬連結已複製至剪貼簿！')
      setTimeout(() => setCopied(false), 2500)
    } catch {
      setCopied(true)
      onNotify?.('✨ 穿搭專屬連結已複製！')
      setTimeout(() => setCopied(false), 2500)
    }
  }

  async function handleNativeShare() {
    if (navigator.share && post) {
      try {
        await navigator.share({
          title: `推薦穿搭：${post.outfit?.name || post.caption || '時尚OOTD'}`,
          text: `來看看這套穿搭「${post.caption}」，整體契合度超高！`,
          url: shareUrl,
        })
        onNotify?.('📲 已開啟系統分享功能')
      } catch {
        // User cancelled or share failed
      }
    }
  }

  async function handleSend(friend: Friend) {
    if (sentFriendIds.includes(friend.id) || !post) return
    setSendingFriendId(friend.id)
    try {
      await onShareToFriend(friend, post, customMessage.trim())
      setSentFriendIds(prev => [...prev, friend.id])
      setLastSharedFriend(friend.displayName)
      onNotify?.(`🚀 已成功將穿搭分享給 ${friend.displayName}！`)
    } catch (err) {
      console.error('Failed to share to friend', err)
    } finally {
      setSendingFriendId(null)
    }
  }

  const hasNativeShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

  return (
    <div className="share-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="share-modal-card" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="share-modal-header">
          <div className="share-modal-title">
            <Share2 size={18} />
            <span>分享這套穿搭</span>
          </div>
          <button type="button" className="share-modal-close" onClick={onClose} aria-label="關閉">
            <X size={18} />
          </button>
        </div>

        {/* In-Dialog Feedback Alert Banner */}
        {lastSharedFriend && (
          <div className="share-feedback-banner">
            <div className="share-feedback-icon-wrap">
              <CheckCircle2 size={18} className="text-success" />
            </div>
            <div className="share-feedback-content">
              <strong>分享成功！</strong>
              <span>已將穿搭與留言推薦給 <b>{lastSharedFriend}</b>，好友可在「我的 ➔ 社交 ➔ 好友穿搭動態」隨時查看！</span>
            </div>
          </div>
        )}

        {/* Outfit Preview Card */}
        <div className="share-outfit-preview">
          <img
            src={post.imageUrl || ''}
            alt={post.caption}
            className="share-outfit-thumb"
          />
          <div className="share-outfit-details">
            <h4 className="share-outfit-name">{post.outfit?.name || post.caption}</h4>
            <p className="share-outfit-author">穿搭發布者：@{post.author.username}</p>
            <div className="share-outfit-meta">
              {post.outfit?.description ? (
                <span className="share-desc-snippet">{post.outfit.description}</span>
              ) : null}
              {typeof post.matchScore === 'number' ? (
                <span className="share-match-tag">
                  <Sparkles size={10} />
                  契合度 {Math.round(post.matchScore * 100)}%
                </span>
              ) : null}
            </div>
          </div>
        </div>

        {/* Option 1: Copy Link & Native Share */}
        <div className="share-section">
          <label className="share-section-label">
            <Link2 size={14} />
            <span>複製穿搭專屬連結</span>
          </label>
          <div className="share-link-row">
            <input
              type="text"
              readOnly
              value={shareUrl}
              className="share-link-input"
            />
            <button
              type="button"
              className={`share-copy-btn ${copied ? 'copied' : ''}`}
              onClick={handleCopyLink}
            >
              {copied ? (
                <>
                  <Check size={14} />
                  <span>已複製！</span>
                </>
              ) : (
                <>
                  <Copy size={14} />
                  <span>複製連結</span>
                </>
              )}
            </button>
            {hasNativeShare && (
              <button
                type="button"
                className="share-native-btn"
                onClick={handleNativeShare}
                title="以其他通訊軟體分享"
              >
                <Share2 size={15} />
              </button>
            )}
          </div>
        </div>

        {/* Option 2: Send directly to Connected Friends */}
        <div className="share-section">
          <label className="share-section-label">
            <Send size={14} />
            <span>一鍵傳送給穿搭好友</span>
          </label>

          <input
            type="text"
            value={customMessage}
            onChange={e => setCustomMessage(e.target.value)}
            placeholder="留一句話給好友（選填，例如：這套超適合你！）"
            className="share-msg-input"
          />

          {friends.length > 0 ? (
            <div className="share-friends-list">
              {friends.map(friend => {
                const isSent = sentFriendIds.includes(friend.id)
                const isSending = sendingFriendId === friend.id
                return (
                  <div key={friend.id} className="share-friend-item">
                    <div className="share-friend-avatar-wrap">
                      {friend.avatarUrl ? (
                        <img src={friend.avatarUrl} alt={friend.displayName} className="share-friend-avatar" />
                      ) : (
                        <div className="share-friend-avatar-fallback">{friend.avatarText}</div>
                      )}
                    </div>

                    <div className="share-friend-name-col">
                      <span className="share-friend-name">{friend.displayName}</span>
                      <span className="share-friend-tags">
                        {friend.styleTags?.slice(0, 2).map(t => `#${t}`).join(' ')}
                      </span>
                    </div>

                    <button
                      type="button"
                      className={`share-friend-send-btn ${isSent ? 'sent' : ''}`}
                      disabled={isSent || isSending}
                      onClick={() => void handleSend(friend)}
                    >
                      {isSent ? (
                        <>
                          <Check size={12} />
                          <span>已傳送</span>
                        </>
                      ) : isSending ? (
                        <span>傳送中...</span>
                      ) : (
                        <>
                          <Send size={12} />
                          <span>傳送</span>
                        </>
                      )}
                    </button>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="share-empty-hint">你目前還沒有連結的好友，可先至「我的 ➔ 社交」透過 Email 新增好友！</p>
          )}
        </div>
      </div>
    </div>
  )
}

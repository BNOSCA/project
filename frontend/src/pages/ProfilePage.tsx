import {
  Bookmark,
  Check,
  LogOut,
  Mail,
  MessageCircle,
  Pencil,
  Send,
  ShoppingBag,
  Sparkles,
  Trash2,
  UserPlus,
  Users,
  X,
} from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'

import { Avatar } from '../components/common/Avatar'
import { OutfitPost } from '../components/post/OutfitPost'
import { addFriendByEmail, getFriends, getSharedOutfits, removeFriend, resetSharedOutfits } from '../services/social'

import type {
  Friend,
  OutfitPost as OutfitPostModel,
  SharedOutfit,
  User,
} from '../types/index'

interface ProfilePageProps {
  user: User

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

  onGoSaved: () => void

  onShare?: (
    post: OutfitPostModel,
  ) => void

  onUpdateProfile: (profile: Pick<User, 'displayName' | 'username' | 'bio' | 'avatarUrl'>) => Promise<void>
  onSignOut: () => Promise<void>
}

export function ProfilePage({
  user,
  posts,
  likedIds,
  savedIds,
  onLike,
  onSave,
  onFindProducts,
  onGoSaved,
  onShare,
  onUpdateProfile,
  onSignOut,
}: ProfilePageProps) {
  const [editing, setEditing] = useState(false)
  const [displayName, setDisplayName] = useState(user.displayName)
  const [username, setUsername] = useState(user.username)
  const [bio, setBio] = useState(user.bio ?? '')
  const [avatarUrl, setAvatarUrl] = useState(user.avatarUrl ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Social Tab States
  const [activeTab, setActiveTab] = useState<'posts' | 'social'>('posts')
  const [friends, setFriends] = useState<Friend[]>([])
  const [sharedOutfits, setSharedOutfits] = useState<SharedOutfit[]>([])
  const [sharedFilter, setSharedFilter] = useState<'all' | 'received' | 'sent'>('all')
  const [emailInput, setEmailInput] = useState('')
  const [addingFriend, setAddingFriend] = useState(false)
  const [socialMessage, setSocialMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    void getFriends(user.id).then(setFriends)
    void getSharedOutfits(user.id).then(setSharedOutfits)
  }, [user.id])

  function handleResetShared() {
    const fresh = resetSharedOutfits(user.id)
    setSharedOutfits(fresh)
    setSocialMessage({ type: 'success', text: '已重置穿搭動態為各好友的精選風格穿搭！' })
  }

  async function handleAddFriend(e: FormEvent) {
    e.preventDefault()
    const trimmed = emailInput.trim()
    if (!trimmed) return

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(trimmed)) {
      setSocialMessage({ type: 'error', text: '請輸入正確格式的電子郵件（例如：friend@example.com）' })
      return
    }

    setAddingFriend(true)
    setSocialMessage(null)
    try {
      const newFriend = await addFriendByEmail(user.id, trimmed)
      setFriends(prev => [newFriend, ...prev])
      setEmailInput('')
      setSocialMessage({ type: 'success', text: `成功將 ${newFriend.displayName} 加為穿搭好友！` })
    } catch (err: any) {
      setSocialMessage({ type: 'error', text: err?.message || '新增好友失敗，請稍後再試' })
    } finally {
      setAddingFriend(false)
    }
  }

  async function handleRemoveFriend(friendId: string) {
    try {
      await removeFriend(user.id, friendId)
      setFriends(prev => prev.filter(f => f.id !== friendId))
      setSocialMessage({ type: 'success', text: '已解除好友連結' })
    } catch (err) {
      console.error('Failed to remove friend', err)
    }
  }

  useEffect(() => {
    setDisplayName(user.displayName)
    setUsername(user.username)
    setBio(user.bio ?? '')
    setAvatarUrl(user.avatarUrl ?? '')
  }, [user])

  async function saveProfile(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSaving(true)
    try {
      await onUpdateProfile({
        displayName: displayName.trim(),
        username: username.trim().replace(/^@/, ''),
        bio: bio.trim(),
        avatarUrl: avatarUrl.trim() || undefined,
      })
      setEditing(false)
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : '無法儲存個人檔案')
    } finally {
      setSaving(false)
    }
  }
  const userPosts =
    posts.filter(
      post =>
        post.author.id ===
        user.id,
    )

  return (
    <section className="profile-page">
      <div className="profile-header">
        <Avatar
          user={user}
          size="large"
          className="profile-avatar"
        />

        <div className="profile-info">
          <div className="profile-name-row">
            <div>
              <h1>
                {user.displayName}
              </h1>

              <span>
                @{user.username}
              </span>
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={() => setEditing(true)}
            >
              <Pencil size={14} />
              編輯個人檔案
            </button>
          </div>

          {user.bio && (
            <p>
              {user.bio}
            </p>
          )}

          <div className="profile-stats">
            <span>
              <strong>
                {
                  user.postCount
                }
              </strong>

              貼文
            </span>

            <span>
              <strong>
                {user.followerCount.toLocaleString()}
              </strong>

              粉絲
            </span>

            <span>
              <strong>
                {user.followingCount.toLocaleString()}
              </strong>

              追蹤中
            </span>
          </div>
        </div>
      </div>

      <button className="profile-signout" type="button" onClick={() => void onSignOut()}>
        <LogOut size={16} />
        登出帳號
      </button>

      {editing && (
        <div className="modal-backdrop" role="presentation" onMouseDown={event => {
          if (event.target === event.currentTarget) setEditing(false)
        }}>
          <section className="profile-editor" role="dialog" aria-modal="true" aria-labelledby="profile-editor-title">
            <button className="icon-button dialog-close" type="button" onClick={() => setEditing(false)} aria-label="關閉">
              <X size={20} />
            </button>
            <h2 id="profile-editor-title">編輯個人檔案</h2>
            <p>更新其他人看到的名稱、帳號與自我介紹。</p>
            <form onSubmit={saveProfile}>
              <label>顯示名稱<input value={displayName} onChange={event => setDisplayName(event.target.value)} maxLength={40} required /></label>
              <label>使用者名稱<div className="username-input"><span>@</span><input value={username} onChange={event => setUsername(event.target.value)} pattern="[A-Za-z0-9._]+" maxLength={30} required /></div></label>
              <label>頭像圖片網址<input type="url" value={avatarUrl} onChange={event => setAvatarUrl(event.target.value)} placeholder="https://..." /></label>
              <label>自我介紹<textarea value={bio} onChange={event => setBio(event.target.value)} maxLength={160} rows={4} /></label>
              <div className="profile-editor-count">{bio.length}/160</div>
              {error && <div className="form-error" role="alert">{error}</div>}
              <button className="primary-button" type="submit" disabled={saving}>{saving ? '儲存中...' : '儲存變更'}</button>
            </form>
          </section>
        </div>
      )}

      <section className="style-profile">
        <div className="style-profile-title">
          <Sparkles
            size={18}
          />

          <strong>
            Your Style Profile
          </strong>
        </div>

        <div className="style-bars">
          <div>
            <span>
              Minimal
            </span>

            <div>
              <i
                style={{
                  width:
                    '88%',
                }}
              />
            </div>

            <strong>
              88%
            </strong>
          </div>

          <div>
            <span>
              Smart Casual
            </span>

            <div>
              <i
                style={{
                  width:
                    '74%',
                }}
              />
            </div>

            <strong>
              74%
            </strong>
          </div>

          <div>
            <span>
              Japanese
            </span>

            <div>
              <i
                style={{
                  width:
                    '62%',
                }}
              />
            </div>

            <strong>
              62%
            </strong>
          </div>
        </div>
      </section>

      <div className="profile-tabs">
        <button
          type="button"
          className={activeTab === 'posts' ? 'active' : ''}
          onClick={() => setActiveTab('posts')}
        >
          貼文
        </button>

        <button
          type="button"
          onClick={onGoSaved}
        >
          收藏
        </button>

        <button
          type="button"
          className={activeTab === 'social' ? 'active' : ''}
          onClick={() => setActiveTab('social')}
        >
          社交 ({friends.length})
        </button>
      </div>

      {activeTab === 'posts' && (
        userPosts.length > 0 ? (
          <div className="discover-grid">
            {userPosts.map(post => (
              <OutfitPost
                key={post.id}
                variant="grid"
                post={post}
                liked={likedIds.includes(post.id)}
                saved={savedIds.includes(post.id)}
                onLike={onLike}
                onSave={onSave}
                onFindProducts={onFindProducts}
                onShare={onShare ? () => onShare(post) : undefined}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <h2>還沒有分享穿搭</h2>
            <p>你的 OOTD 之後會出現在這裡。</p>
          </div>
        )
      )}

      {activeTab === 'social' && (
        <div className="social-container">
          {/* Email Add Friend Box */}
          <div className="social-invite-card">
            <div className="social-invite-header">
              <div className="social-invite-title">
                <UserPlus size={18} />
                <span>透過郵箱加好友</span>
              </div>
              <p className="social-invite-desc">輸入好友的 Email，建立穿搭品味連結，解鎖更多穿搭推薦互動！</p>
            </div>

            <form onSubmit={handleAddFriend} className="social-invite-form">
              <div className="social-input-wrapper">
                <Mail size={16} className="social-input-icon" />
                <input
                  type="email"
                  value={emailInput}
                  onChange={e => setEmailInput(e.target.value)}
                  placeholder="例如：friend@example.com"
                  className="social-email-input"
                  disabled={addingFriend}
                />
              </div>
              <button
                type="submit"
                className="social-invite-btn"
                disabled={addingFriend || !emailInput.trim()}
              >
                {addingFriend ? '邀請中...' : '加為好友'}
              </button>
            </form>

            {socialMessage && (
              <div className={`social-feedback-alert ${socialMessage.type}`}>
                {socialMessage.type === 'success' ? <Check size={15} /> : <X size={15} />}
                <span>{socialMessage.text}</span>
              </div>
            )}
          </div>

          {/* Connected Friends List */}
          <div className="social-friends-header">
            <div className="social-friends-title">
              <Users size={18} />
              <span>已連結的好友 ({friends.length})</span>
            </div>
            <span className="social-friends-hint">點擊可查看朋友的 OOTD 與風格契合度</span>
          </div>

          {friends.length > 0 ? (
            <div className="social-friends-grid">
              {friends.map(friend => (
                <div key={friend.id} className="social-friend-card">
                  <div className="social-friend-avatar-wrap">
                    {friend.avatarUrl ? (
                      <img src={friend.avatarUrl} alt={friend.displayName} className="social-friend-avatar-img" />
                    ) : (
                      <div className="social-friend-avatar-text">{friend.avatarText}</div>
                    )}
                    {typeof friend.matchPercentage === 'number' && (
                      <span className="social-friend-match-badge" title="穿搭風格契合度">
                        <Sparkles size={11} />
                        {friend.matchPercentage}% 契合
                      </span>
                    )}
                  </div>

                  <div className="social-friend-info">
                    <div className="social-friend-name-row">
                      <div className="social-friend-name-group">
                        <h3 className="social-friend-name">{friend.displayName}</h3>
                        <span className="social-friend-username">@{friend.username}</span>
                      </div>
                      <button
                        type="button"
                        className="social-friend-remove-btn"
                        onClick={() => void handleRemoveFriend(friend.id)}
                        title="解除好友連結"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>

                    <p className="social-friend-email">
                      <Mail size={12} />
                      <span>{friend.email}</span>
                    </p>

                    {friend.styleTags && friend.styleTags.length > 0 && (
                      <div className="social-friend-tags">
                        {friend.styleTags.map(tag => (
                          <span key={tag} className="social-friend-tag">#{tag}</span>
                        ))}
                      </div>
                    )}

                    <div className="social-friend-footer">
                      <span className="social-friend-status">● 已建立連結</span>
                      <span className="social-friend-date">{friend.connectedAt}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <h2>目前還沒有連結的好友</h2>
              <p>在上方輸入好友的 Email，立即建立穿搭專屬社交圈！</p>
            </div>
          )}

          {/* Friends' Shared Outfits Showcase (好友穿搭動態＆分享箱) */}
          {/* Friends' Shared Outfits Showcase (好友穿搭動態＆分享箱) */}
          <div className="social-friends-header" style={{ marginTop: '28px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: '8px' }}>
              <div className="social-friends-title">
                <Sparkles size={18} />
                <span>好友穿搭分享動態 ({sharedOutfits.length})</span>
              </div>
              <button
                type="button"
                className="social-reset-feed-btn"
                onClick={handleResetShared}
                title="重置為好友預設推薦穿搭"
              >
                重置推薦動態
              </button>
            </div>
            <span className="social-friends-hint">好友傳送給你的精選 OOTD 與穿搭推薦</span>

            {/* Sub-filter tabs */}
            <div className="social-shared-filter-row">
              <button
                type="button"
                className={`social-filter-tab ${sharedFilter === 'all' ? 'active' : ''}`}
                onClick={() => setSharedFilter('all')}
              >
                全部 ({sharedOutfits.length})
              </button>
              <button
                type="button"
                className={`social-filter-tab ${sharedFilter === 'received' ? 'active' : ''}`}
                onClick={() => setSharedFilter('received')}
              >
                好友推薦給我 ({sharedOutfits.filter(s => s.fromUser.id !== user.id).length})
              </button>
              <button
                type="button"
                className={`social-filter-tab ${sharedFilter === 'sent' ? 'active' : ''}`}
                onClick={() => setSharedFilter('sent')}
              >
                我分享出去的 ({sharedOutfits.filter(s => s.fromUser.id === user.id).length})
              </button>
            </div>
          </div>

          {sharedOutfits.filter(item => {
            if (sharedFilter === 'received') return item.fromUser.id !== user.id
            if (sharedFilter === 'sent') return item.fromUser.id === user.id
            return true
          }).length > 0 ? (
            <div className="social-shared-grid">
              {sharedOutfits.filter(item => {
                if (sharedFilter === 'received') return item.fromUser.id !== user.id
                if (sharedFilter === 'sent') return item.fromUser.id === user.id
                return true
              }).map(item => (
                <div key={item.id} className="social-shared-card">
                  <div className="social-shared-banner">
                    <div className="social-shared-from">
                      {item.fromUser.avatarUrl ? (
                        <img src={item.fromUser.avatarUrl} alt={item.fromUser.displayName} className="social-shared-avatar" />
                      ) : (
                        <span className="social-shared-avatar-text">{item.fromUser.avatarText}</span>
                      )}
                      <div>
                        <span className="social-shared-sender">
                          {item.fromUser.id === user.id ? (
                            <>你 分享給 <b>@{item.toFriendName}</b></>
                          ) : (
                            <>由 <b>{item.fromUser.displayName}</b> 分享推薦</>
                          )}
                        </span>
                        <span className="social-shared-time">{item.sharedAt}</span>
                      </div>
                    </div>
                    {typeof item.matchPercentage === 'number' && (
                      <span className="social-shared-match-pill">
                        <Sparkles size={11} />
                        {item.matchPercentage}% 風格契合
                      </span>
                    )}
                  </div>

                  {item.message && (
                    <div className="social-shared-message">
                      <MessageCircle size={13} />
                      <p>「{item.message}」</p>
                    </div>
                  )}

                  <div className="social-shared-body">
                    <img
                      src={item.post.imageUrl || ''}
                      alt={item.post.caption}
                      className="social-shared-img"
                    />
                    <div className="social-shared-content">
                      <h4 className="social-shared-outfit-name">{item.post.outfit?.name || item.post.caption}</h4>
                      <p className="social-shared-caption">{item.post.caption}</p>
                      {item.post.outfit?.description && (
                        <span className="social-shared-desc-tag">{item.post.outfit.description}</span>
                      )}

                      <div className="social-shared-actions">
                        <button
                          type="button"
                          className="social-shared-btn primary"
                          onClick={() => onFindProducts(item.post)}
                        >
                          <ShoppingBag size={13} />
                          <span>尋找相似單品</span>
                        </button>
                        <button
                          type="button"
                          className="social-shared-btn secondary"
                          onClick={() => onSave(item.post.id)}
                        >
                          <Bookmark size={13} fill={savedIds.includes(item.post.id) ? 'currentColor' : 'none'} />
                          <span>{savedIds.includes(item.post.id) ? '已收藏' : '收藏'}</span>
                        </button>
                        {onShare && (
                          <button
                            type="button"
                            className="social-shared-btn secondary"
                            onClick={() => onShare(item.post)}
                            title="轉發給其他人"
                          >
                            <Send size={13} />
                            <span>轉發</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>目前還沒有好友分享的穿搭，點擊貼文上的「分享」圖示即可傳送穿搭給好友！</p>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

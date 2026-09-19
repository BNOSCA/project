import {
  LogOut,
  Pencil,
  Sparkles,
  X,
} from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'

import { Avatar } from '../components/common/Avatar'
import { OutfitPost } from '../components/post/OutfitPost'

import type {
  OutfitPost as OutfitPostModel,
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
          className="active"
        >
          貼文
        </button>

        <button
          type="button"
          onClick={onGoSaved}
        >
          收藏
        </button>
      </div>

      {userPosts.length >
      0 ? (
        <div className="discover-grid">
          {userPosts.map(
            post => (
              <OutfitPost
                key={post.id}
                variant="grid"
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
        </div>
      ) : (
        <div className="empty-state">
          <h2>
            還沒有分享穿搭
          </h2>

          <p>
            你的 OOTD
            之後會出現在這裡。
          </p>
        </div>
      )}
    </section>
  )
}

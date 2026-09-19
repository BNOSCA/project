import {
  Sparkles,
} from 'lucide-react'

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
}: ProfilePageProps) {
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
            >
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
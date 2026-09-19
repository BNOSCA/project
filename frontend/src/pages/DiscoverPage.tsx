import {
  Search,
  Sparkles,
  X,
} from 'lucide-react'

import {
  useMemo,
  useState,
} from 'react'

import { OutfitPost } from '../components/post/OutfitPost'

import type {
  OutfitPost as OutfitPostModel,
} from '../types/index'

interface DiscoverPageProps {
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
}

const styleTags = [
  'For You',
  'Minimal',
  'Streetwear',
  'Office',
  'Interview',
  'Date',
  'Summer',
  'Korean',
]

function normalize(
  value: string,
) {
  return value
    .trim()
    .toLowerCase()
}

export function DiscoverPage({
  posts,
  likedIds,
  savedIds,
  onLike,
  onSave,
  onFindProducts,
}: DiscoverPageProps) {
  const [
    search,
    setSearch,
  ] = useState('')

  const [
    selectedTag,
    setSelectedTag,
  ] = useState(
    'For You',
  )

  const filteredPosts =
    useMemo(() => {
      const keyword =
        normalize(search)

      const tag =
        normalize(
          selectedTag,
        )

      return posts.filter(
        post => {
          const searchableText =
            [
              post.caption,

              post.outfit.name,

              post.outfit
                .description,

              ...post.outfit
                .styles,

              ...post.outfit
                .occasions,

              ...post.outfit.items
                .map(
                  item =>
                    item.name,
                ),
            ]
              .join(' ')
              .toLowerCase()

          const matchesSearch =
            !keyword ||
            searchableText.includes(
              keyword,
            )

          const matchesTag =
            selectedTag ===
              'For You' ||
            searchableText.includes(
              tag,
            )

          return (
            matchesSearch &&
            matchesTag
          )
        },
      )
    }, [
      posts,
      search,
      selectedTag,
    ])

  return (
    <section className="page-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">
            DISCOVER
          </span>

          <h1>
            找到下一套靈感。
          </h1>

          <p>
            從穿搭、風格與場合探索社群內容。
          </p>
        </div>
      </div>

      <div className="search-box">
        <Search size={19} />

        <input
          type="search"
          value={search}
          placeholder="搜尋穿搭、風格、場合..."
          aria-label="搜尋穿搭"
          onChange={event =>
            setSearch(
              event.target.value,
            )
          }
        />

        {search && (
          <button
            type="button"
            aria-label="清除搜尋"
            onClick={() =>
              setSearch('')
            }
          >
            <X size={17} />
          </button>
        )}
      </div>

      <div className="tag-row">
        {styleTags.map(
          tag => (
            <button
              key={tag}
              type="button"
              className={
                selectedTag ===
                tag
                  ? 'active'
                  : ''
              }
              onClick={() =>
                setSelectedTag(
                  tag,
                )
              }
            >
              {tag}
            </button>
          ),
        )}
      </div>

      <div className="discover-summary">
        <div>
          <Sparkles
            size={18}
          />

          <span>
            根據你的收藏與互動，
            優先探索符合個人風格的穿搭。
          </span>
        </div>
      </div>

      {filteredPosts.length >
      0 ? (
        <div className="discover-grid">
          {filteredPosts.map(
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
          <Search size={30} />

          <h2>
            沒有找到符合的穿搭
          </h2>

          <p>
            換個關鍵字或風格看看。
          </p>
        </div>
      )}
    </section>
  )
}
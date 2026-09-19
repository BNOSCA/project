import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import { Toast } from './components/common/Toast'

import { BottomNav } from './components/layout/BottomNav'
import { MobileHeader } from './components/layout/MobileHeader'
import { RightSidebar } from './components/layout/RightSidebar'
import { Sidebar } from './components/layout/Sidebar'

import { SimilarProducts } from './components/product/SimilarProducts'

import {
  currentUser,
  mockPosts,
  mockProducts,
} from './data'

import {
  CreatePostPage,
  type CreatePostDraft,
} from './pages/CreatePostPage'

import { DiscoverPage } from './pages/DiscoverPage'
import { HomePage } from './pages/HomePage'
import { ProfilePage } from './pages/ProfilePage'
import { SavedPage } from './pages/SavedPage'

import type {
  AppPage,
  OutfitPost,
  Product,
} from './types/index'

const likedStorageKey =
  'loop:liked-posts:v1'

const savedStorageKey =
  'loop:saved-posts:v1'

function readStoredIds(
  key: string,
): string[] {
  try {
    const raw =
      localStorage.getItem(
        key,
      )

    if (!raw) {
      return []
    }

    const parsed: unknown =
      JSON.parse(raw)

    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.filter(
      (
        value,
      ): value is string =>
        typeof value ===
        'string',
    )
  } catch {
    return []
  }
}

function updateIdList(
  current: string[],
  id: string,
) {
  return current.includes(id)
    ? current.filter(
        item => item !== id,
      )
    : [
        ...current,
        id,
      ]
}

export default function App() {
  const [
    currentPage,
    setCurrentPage,
  ] =
    useState<AppPage>(
      'home',
    )

  const [
    posts,
    setPosts,
  ] =
    useState<OutfitPost[]>(
      mockPosts,
    )

  const [
    likedIds,
    setLikedIds,
  ] = useState<string[]>(
    () =>
      readStoredIds(
        likedStorageKey,
      ),
  )

  const [
    savedIds,
    setSavedIds,
  ] = useState<string[]>(
    () =>
      readStoredIds(
        savedStorageKey,
      ),
  )

  const [
    selectedProductPost,
    setSelectedProductPost,
  ] =
    useState<OutfitPost | null>(
      null,
    )

  const [
    notice,
    setNotice,
  ] = useState('')

  /*
   * Demo 上傳的圖片使用 Object URL。
   *
   * App unmount 時統一釋放，
   * 避免長時間開發時累積 memory。
   */
  const generatedImageUrls =
    useRef<string[]>([])

  useEffect(() => {
    return () => {
      generatedImageUrls
        .current
        .forEach(url => {
          URL.revokeObjectURL(
            url,
          )
        })
    }
  }, [])

  /*
   * Toast 自動消失。
   */
  useEffect(() => {
    if (!notice) {
      return
    }

    const timeout =
      window.setTimeout(
        () => {
          setNotice('')
        },
        2200,
      )

    return () =>
      window.clearTimeout(
        timeout,
      )
  }, [notice])

  /*
   * 找與目前 Outfit Item category
   * 相符的商品。
   *
   * 目前：
   * category filter
   * → similarity sort
   *
   * 未來：
   * embedding search
   * → vector similarity
   */
  const similarProducts =
    useMemo(() => {
      if (
        !selectedProductPost
      ) {
        return []
      }

      const categories =
        new Set(
          selectedProductPost
            .outfit
            .items
            .map(
              item =>
                item.category,
            ),
        )

      return mockProducts
        .filter(product =>
          categories.has(
            product.category,
          ),
        )
        .sort(
          (a, b) =>
            (
              b.similarity ??
              0
            ) -
            (
              a.similarity ??
              0
            ),
        )
        .slice(0, 8)
    }, [
      selectedProductPost,
    ])

  function navigate(
    page: AppPage,
  ) {
    setCurrentPage(page)

    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    })
  }

  function toggleLike(
    postId: string,
  ) {
    setLikedIds(
      current => {
        const next =
          updateIdList(
            current,
            postId,
          )

        localStorage.setItem(
          likedStorageKey,
          JSON.stringify(
            next,
          ),
        )

        return next
      },
    )
  }

  function toggleSave(
    postId: string,
  ) {
    setSavedIds(
      current => {
        const wasSaved =
          current.includes(
            postId,
          )

        const next =
          updateIdList(
            current,
            postId,
          )

        localStorage.setItem(
          savedStorageKey,
          JSON.stringify(
            next,
          ),
        )

        setNotice(
          wasSaved
            ? '已從收藏移除'
            : '已收藏這套穿搭',
        )

        return next
      },
    )
  }

  function openProducts(
    post: OutfitPost,
  ) {
    setSelectedProductPost(
      post,
    )
  }

  function closeProducts() {
    setSelectedProductPost(
      null,
    )
  }

  function openProduct(
    product: Product,
  ) {
    if (
      product.productUrl
    ) {
      window.open(
        product.productUrl,
        '_blank',
        'noopener,noreferrer',
      )

      return
    }

    setNotice(
      `${product.brand} ${
        product.name
      }：Demo 尚未串接真實商品頁`,
    )
  }

  /*
   * Demo Publish
   *
   * 現在：
   * 1. 使用者上傳圖片
   * 2. 建立本地 Object URL
   * 3. 建立一篇 OutfitPost
   *
   * 未來：
   *
   * Image
   * ↓
   * Supabase Storage
   * ↓
   * Vision AI
   * ↓
   * Outfit Parsing
   * ↓
   * posts / outfits / outfit_items
   */
  function publishPost(
    draft: CreatePostDraft,
  ) {
    const imageUrl =
      URL.createObjectURL(
        draft.imageFile,
      )

    generatedImageUrls
      .current
      .push(imageUrl)

    const timestamp =
      Date.now()

    const newPost: OutfitPost =
      {
        id: `post-user-${timestamp}`,

        author:
          currentUser,

        caption:
          draft.caption ||
          '今天的 OOTD。',

        imageUrl,

        outfit: {
          id: `outfit-user-${timestamp}`,

          name:
            'My Daily OOTD',

          description:
            '使用者分享的穿搭。AI Vision 尚未串接，目前使用示範標籤。',

          styles: [
            'Personal',
            'Daily',
          ],

          occasions: [
            'Daily',
          ],

          season: [
            'All Season',
          ],

          formality:
            0.5,

          items: [
            {
              id: `item-user-${timestamp}-top`,

              category:
                'top',

              name:
                'Detected Top',

              color:
                '#e4e1da',

              style:
                'Pending AI',
            },

            {
              id: `item-user-${timestamp}-bottom`,

              category:
                'bottom',

              name:
                'Detected Bottom',

              color:
                '#55575a',

              style:
                'Pending AI',
            },

            {
              id: `item-user-${timestamp}-shoes`,

              category:
                'shoes',

              name:
                'Detected Shoes',

              color:
                '#d8d6d0',

              style:
                'Pending AI',
            },
          ],
        },

        stats: {
          likeCount: 0,
          commentCount: 0,
          saveCount: 0,
        },

        viewerState: {
          liked: false,
          saved: false,
        },

        /*
         * 自己的貼文不需要
         * Personalized Match Score。
         */
        createdAt:
          new Date()
            .toISOString(),
      }

    setPosts(
      current => [
        newPost,
        ...current,
      ],
    )

    setNotice(
      '穿搭已發布',
    )

    navigate('home')
  }

  function renderPage() {
    if (
      currentPage ===
      'discover'
    ) {
      return (
        <DiscoverPage
          posts={posts}
          likedIds={
            likedIds
          }
          savedIds={
            savedIds
          }
          onLike={
            toggleLike
          }
          onSave={
            toggleSave
          }
          onFindProducts={
            openProducts
          }
        />
      )
    }

    if (
      currentPage ===
      'post'
    ) {
      return (
        <CreatePostPage
          currentUser={
            currentUser
          }
          onPublish={
            publishPost
          }
        />
      )
    }

    if (
      currentPage ===
      'saved'
    ) {
      return (
        <SavedPage
          posts={posts}
          likedIds={
            likedIds
          }
          savedIds={
            savedIds
          }
          onLike={
            toggleLike
          }
          onSave={
            toggleSave
          }
          onFindProducts={
            openProducts
          }
          onGoHome={() =>
            navigate('home')
          }
        />
      )
    }

    if (
      currentPage ===
      'profile'
    ) {
      return (
        <ProfilePage
          user={
            currentUser
          }
          posts={
            posts
          }
          likedIds={
            likedIds
          }
          savedIds={
            savedIds
          }
          onLike={
            toggleLike
          }
          onSave={
            toggleSave
          }
          onFindProducts={
            openProducts
          }
          onGoSaved={() =>
            navigate('saved')
          }
        />
      )
    }

    return (
      <HomePage
        currentUser={
          currentUser
        }
        posts={
          posts
        }
        likedIds={
          likedIds
        }
        savedIds={
          savedIds
        }
        onLike={
          toggleLike
        }
        onSave={
          toggleSave
        }
        onFindProducts={
          openProducts
        }
        onCreatePost={() =>
          navigate('post')
        }
      />
    )
  }

  return (
    <div className="social-app">
      <Toast
        message={notice}
      />

      <div className="app-layout">
        <Sidebar
          currentPage={
            currentPage
          }
          currentUser={
            currentUser
          }
          onNavigate={
            navigate
          }
        />

        <main className="main-column">
          <MobileHeader
            onSearch={() =>
              navigate(
                'discover',
              )
            }
          />

          {renderPage()}
        </main>

        <RightSidebar
          onDiscover={() =>
            navigate(
              'discover',
            )
          }
        />
      </div>

      <BottomNav
        currentPage={
          currentPage
        }
        onNavigate={
          navigate
        }
      />

      {selectedProductPost && (
        <SimilarProducts
          sourceItems={
            selectedProductPost
              .outfit
              .items
          }
          products={
            similarProducts
          }
          onClose={
            closeProducts
          }
          onOpenProduct={
            openProduct
          }
        />
      )}
    </div>
  )
}
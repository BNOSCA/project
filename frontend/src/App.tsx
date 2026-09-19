import {
  useEffect,
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
import { ShopPage } from './pages/ShopPage'

import {
  loadRecommendedFeed,
  loadPostProducts,
  recordPostInteraction,
  recordPostLike,
  recordPostSave,
  recordProductClick,
} from './services/feed'
import { getRequestIdentity } from './services/auth'

import type {
  AppPage,
  OutfitPost,
  Product,
} from './types/index'

function likedStorageKey(userId: string) {
  return `loop:liked-posts:${userId}:v1`
}

function savedStorageKey(userId: string) {
  return `loop:saved-posts:${userId}:v1`
}

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

function demoProductsForPost(post: OutfitPost): Product[] {
  const categories = new Set(post.outfit.items.map(item => item.category))
  return mockProducts
    .filter(product => categories.has(product.category))
    .sort((a, b) => (b.similarity ?? 0) - (a.similarity ?? 0))
    .slice(0, 8)
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
  ] = useState<string[]>([])

  const [
    savedIds,
    setSavedIds,
  ] = useState<string[]>([])

  const [activeUserId, setActiveUserId] = useState('anonymous-demo')

  const [
    selectedProductPost,
    setSelectedProductPost,
  ] =
    useState<OutfitPost | null>(
      null,
    )

  const [similarProducts, setSimilarProducts] = useState<Product[]>([])
  const [productsLoading, setProductsLoading] = useState(false)
  const [productsAreDemo, setProductsAreDemo] = useState(false)
  const productDwell = useRef<{ activeFrom: number | null; elapsedMs: number }>({
    activeFrom: null,
    elapsedMs: 0,
  })

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

  useEffect(() => {
    let active = true
    void getRequestIdentity()
      .then(identity => {
        if (active) setActiveUserId(identity.userId)
      })
      .catch(() => {
        // Keep the local fallback identity when Firebase is unavailable.
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    setLikedIds(readStoredIds(likedStorageKey(activeUserId)))
    setSavedIds(readStoredIds(savedStorageKey(activeUserId)))
  }, [activeUserId])

  useEffect(() => {
    function trackVisibility() {
      const dwell = productDwell.current
      if (document.visibilityState === 'hidden' && dwell.activeFrom !== null) {
        dwell.elapsedMs += Date.now() - dwell.activeFrom
        dwell.activeFrom = null
      } else if (document.visibilityState === 'visible' && dwell.activeFrom === null && selectedProductPost) {
        dwell.activeFrom = Date.now()
      }
    }
    document.addEventListener('visibilitychange', trackVisibility)
    return () => document.removeEventListener('visibilitychange', trackVisibility)
  }, [selectedProductPost])

  async function refreshFeed() {
    const recommendedPosts = await loadRecommendedFeed()
    if (recommendedPosts.length > 0) {
      setPosts(current => [
        ...current.filter(post => post.id.startsWith('post-user-')),
        ...recommendedPosts,
      ])
    }
  }

  /*
   * 優先使用本機 FastAPI 的推薦 feed；後端未啟動時保留
   * 內建 mock，讓純前端開發仍可使用。
   */
  useEffect(() => {
    let active = true

    loadRecommendedFeed()
      .then(recommendedPosts => {
        if (active) {
          setPosts(current => [
            ...current.filter(post => post.id.startsWith('post-user-')),
            ...recommendedPosts,
          ])
        }
      })
      .catch(() => {
        if (active) setNotice('後端未連線，顯示本機示範貼文')
      })

    return () => {
      active = false
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

  useEffect(() => {
    if (!selectedProductPost) return
    let active = true
    const localPost = selectedProductPost.id.startsWith('post-user-') ||
      mockPosts.some(post => post.id === selectedProductPost.id)
    if (localPost) {
      setSimilarProducts(demoProductsForPost(selectedProductPost))
      setProductsAreDemo(true)
      setProductsLoading(false)
    } else {
      setSimilarProducts([])
      setProductsAreDemo(false)
      setProductsLoading(true)
      loadPostProducts(selectedProductPost.id)
        .then(products => {
          if (active) setSimilarProducts(products)
        })
        .catch(() => {
          if (active) setNotice('目前無法取得這篇貼文的商品')
        })
        .finally(() => {
          if (active) setProductsLoading(false)
        })
    }
    return () => { active = false }
  }, [selectedProductPost])

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
    const isAdding =
      !likedIds.includes(postId)

    setLikedIds(
      current => {
        const next =
          updateIdList(
            current,
            postId,
          )

        localStorage.setItem(
          likedStorageKey(activeUserId),
          JSON.stringify(
            next,
          ),
        )

        return next
      },
    )

    if (isAdding && !postId.startsWith('post-user-') &&
        !mockPosts.some(post => post.id === postId)) {
      void recordPostLike(postId).then(refreshFeed).catch(() => {
        setNotice('已在本機按讚；推薦回饋暫時無法送出')
      })
    }
  }

  function toggleSave(
    postId: string,
  ) {
    const isAdding =
      !savedIds.includes(postId)

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
          savedStorageKey(activeUserId),
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

    if (isAdding && !postId.startsWith('post-user-') &&
        !mockPosts.some(post => post.id === postId)) {
      void recordPostSave(postId).then(refreshFeed).catch(() => {
        setNotice('已儲存在瀏覽器；收藏互動暫時無法送出')
      })
    }
  }

  function openProducts(
    post: OutfitPost,
  ) {
    productDwell.current = {
      activeFrom: document.visibilityState === 'visible' ? Date.now() : null,
      elapsedMs: 0,
    }
    if (!post.id.startsWith('post-user-') && !mockPosts.some(item => item.id === post.id)) {
      void recordPostInteraction(post.id, 'post_open').catch(() => {})
    }
    setSelectedProductPost(
      post,
    )
  }

  function closeProducts() {
    const post = selectedProductPost
    const dwell = productDwell.current
    const dwellMs = Math.min(dwell.elapsedMs +
      (dwell.activeFrom === null ? 0 : Date.now() - dwell.activeFrom), 30000)
    if (post &&
        !post.id.startsWith('post-user-') && !mockPosts.some(item => item.id === post.id)) {
      if (dwellMs >= 2000) {
        void recordPostInteraction(post.id, 'dwell', dwellMs).catch(() => {})
      }
    }
    productDwell.current = { activeFrom: null, elapsedMs: 0 }
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
      if (!product.id.startsWith('product-')) {
        void recordProductClick(product.id).catch(() => {})
      }
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
    if (currentPage === 'shop') {
      return <ShopPage onOpenProduct={openProduct} />
    }

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
        onRefreshFeed={refreshFeed}
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
          isLoading={productsLoading}
          isDemo={productsAreDemo}
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

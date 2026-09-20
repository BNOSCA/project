import {
  useEffect,
  useRef,
  useState,
} from 'react'

import { Toast } from './components/common/Toast'
import { AuthDialog } from './components/auth/AuthDialog'
import { OnboardingDialog } from './components/onboarding/OnboardingDialog'

import { BottomNav } from './components/layout/BottomNav'
import { MobileHeader } from './components/layout/MobileHeader'
import { RightSidebar } from './components/layout/RightSidebar'
import { Sidebar } from './components/layout/Sidebar'

import { SimilarProducts } from './components/product/SimilarProducts'

import {
  currentUser as demoUser,
  mockProducts,
} from './data'

import {
  CreatePostPage,
  type CreatePostDraft,
} from './pages/CreatePostPage'

import { DiscoverPage } from './pages/DiscoverPage'
import { HomePage } from './pages/HomePage'
import { ProfilePage } from './pages/ProfilePage'
import { InsightsPage } from './pages/InsightsPage'
import { SavedPage } from './pages/SavedPage'
import { ShopPage } from './pages/ShopPage'

import {
  loadRecommendedFeed,
  loadPostProducts,
  searchCatalogProducts,
  recordPostInteraction,
  recordPostImpression,
  recordProductClick,
} from './services/feed'
import {
  observeAuthState,
  signOutCurrentUser,
} from './services/auth'
import { loadAdminStatus } from './services/admin'
import { loadAccount, savePublicProfile, saveOnboardingProfile, type AgeRange, type StyleOption } from './services/profile'
import { loadAccountPosts } from './services/feed'
import { changePostState, publishCloudPost } from './services/postState'
import { flushEvents } from './services/eventQueue'

import type {
  AppPage,
  Friend,
  OutfitPost,
  Product,
  User,
} from './types/index'
import { ShareOutfitDialog } from './components/social/ShareOutfitDialog'
import { getFriends, shareOutfitToFriend } from './services/social'


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
  const targetCats = new Set<string>()
  if (post.outfit?.items) {
    for (const item of post.outfit.items) {
      targetCats.add(item.category)
      if (item.category === 'outerwear') targetCats.add('top')
      if (item.category === 'top') targetCats.add('outerwear')
    }
  }
  const styles = (post.outfit?.styles ?? []).map(s => s.toLowerCase())
  if (styles.some(s => s.includes('outdoor') || s.includes('workwear') || s.includes('機能') || s.includes('風衣') || s.includes('山系'))) {
    targetCats.add('outerwear')
  }

  // Filter candidates matching target categories
  let matched = mockProducts.filter(p => targetCats.has(p.category))
  if (matched.length < 4) {
    // Fill up so user always has rich interactive items to browse
    const remaining = mockProducts.filter(p => !matched.some(m => m.id === p.id))
    matched = [...matched, ...remaining]
  }

  return matched
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
      [],
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
  const [currentUser, setCurrentUser] = useState<User>(demoUser)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [accountPosts, setAccountPosts] = useState<OutfitPost[]>([])
  const [followedCreatorIds, setFollowedCreatorIds] = useState<string[]>([])
  const [accountError, setAccountError] = useState('')
  const [accountReload, setAccountReload] = useState(0)
  const currentUid = useRef('anonymous-demo')
  const authGeneration = useRef(0)
  const changingStates = useRef(new Set<string>())
  const [authConfigured, setAuthConfigured] = useState(false)
  const [authDialogOpen, setAuthDialogOpen] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const [onboardingOpen, setOnboardingOpen] = useState(false)
  const [onboardingUserId, setOnboardingUserId] = useState('')

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

  useEffect(() => {
    let disposed = false
    const unsubscribe = observeAuthState(({ user, configured, loading }) => {
      if (loading) return
      const generation = ++authGeneration.current
      const stillCurrent = () => !disposed && authGeneration.current === generation
      const signedIn = Boolean(user && !user.isAnonymous)
      currentUid.current = signedIn && user ? user.uid : 'anonymous-demo'
      setAuthConfigured(configured)
      setIsAuthenticated(signedIn)
      setIsAdmin(false)
      setLikedIds([])
      setSavedIds([])
      setPosts([])
      setAccountPosts([])
      setFollowedCreatorIds([])
      setOnboardingOpen(false)
      setOnboardingUserId('')
      setAccountError('')
      if (!signedIn || !user) {
        setCurrentPage('home')
        setActiveUserId('anonymous-demo')
        setCurrentUser(demoUser)
        return
      }
      setActiveUserId(user.uid)
      const emailName = user.email?.split('@')[0] || 'loop.user'
      const fallback: User = {
        id: user.uid, username: emailName.replace(/[^a-zA-Z0-9._]/g, ''),
        displayName: user.displayName || emailName,
        avatarText: (user.displayName || emailName).slice(0, 1).toUpperCase(),
        avatarUrl: user.photoURL || undefined, bio: '',
        postCount: 0, followerCount: 0, followingCount: 0,
      }
      setCurrentUser(fallback)
      void loadAdminStatus().then(status => {
        if (stillCurrent()) setIsAdmin(status.is_admin)
      }).catch(error => {
        if (stillCurrent()) setAccountError(error instanceof Error ? error.message : '管理權限無法確認')
      })
      void loadAccount(user.uid).then(async account => {
        if (!stillCurrent()) return
        const publicProfile = account.profile?.public_profile
        if (!publicProfile) {
          await savePublicProfile(user.uid, {
            displayName: fallback.displayName, username: fallback.username, bio: '',
            avatarUrl: fallback.avatarUrl,
          })
          if (!stillCurrent()) return
        }
        setCurrentUser({ ...fallback, ...publicProfile,
          avatarText: (publicProfile?.displayName || fallback.displayName).slice(0, 1).toUpperCase(),
          followingCount: account.profile?.followed_creator_ids?.length ?? 0 })
        setLikedIds(account.liked_ids)
        setSavedIds(account.saved_ids)
        setFollowedCreatorIds(account.profile?.followed_creator_ids ?? [])
        setOnboardingUserId(user.uid)
        setOnboardingOpen(!account.profile?.onboarding_completed)
      }).catch(error => {
        if (stillCurrent()) setAccountError(error instanceof Error ? error.message : '帳號資料無法載入')
      })
    })
    return () => { disposed = true; unsubscribe() }
  }, [accountReload])

  useEffect(() => {
    if (!isAuthenticated) return
    let active = true
    void Promise.all([loadAccountPosts('saved'), loadAccountPosts('own')]).then(([saved, own]) => {
      if (!active) return
      setAccountPosts([...new Map([...saved, ...own].map(post => [post.id, post])).values()])
      setCurrentUser(user => ({ ...user, postCount: own.length }))
    }).catch(error => { if (active) setAccountError(error instanceof Error ? error.message : '貼文無法載入') })
    return () => { active = false }
  }, [activeUserId, isAuthenticated, savedIds, accountReload])

  useEffect(() => {
    if (!isAuthenticated) return
    const retry = () => { void flushEvents().catch(() => setNotice('互動尚未同步，連線恢復後會重試')) }
    retry()
    const timer = window.setInterval(retry, 15000)
    window.addEventListener('online', retry)
    return () => { window.clearInterval(timer); window.removeEventListener('online', retry) }
  }, [activeUserId, isAuthenticated])

  // Share Outfit Dialog State
  const [sharePost, setSharePost] = useState<OutfitPost | null>(null)
  const [socialFriends, setSocialFriends] = useState<Friend[]>([])

  useEffect(() => {
    void getFriends(activeUserId).then(setSocialFriends)
  }, [activeUserId])

  function handleOpenShare(post: OutfitPost) {
    setSharePost(post)
  }

  async function handleShareToFriend(friend: Friend, post: OutfitPost, message?: string) {
    await shareOutfitToFriend(activeUserId, currentUser, friend, post, message)
    setNotice(`已成功將穿搭分享給 ${friend.displayName}！`)
  }

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
    const uid = currentUid.current
    try {
      const recommendedPosts = await loadRecommendedFeed()
      if (currentUid.current !== uid) return
      setPosts(recommendedPosts)
      setNotice(recommendedPosts.length > 0 ? '已更新推薦貼文' : '你已看完目前所有貼文')
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : '推薦載入失敗')
    }
  }

  function recordImpression(postId: string, position: number) {
    if (!isAuthenticated) return
    void recordPostImpression(postId, position).catch(() => setNotice('曝光紀錄等待同步'))
  }

  useEffect(() => {
    if (!isAuthenticated) return
    let active = true
    loadRecommendedFeed().then(data => { if (active) setPosts(data) })
      .catch(error => { if (active) setAccountError(error instanceof Error ? error.message : '推薦載入失敗') })
    return () => { active = false }
  }, [activeUserId, isAuthenticated, accountReload])

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
    setSimilarProducts([])
    setProductsAreDemo(false)
    setProductsLoading(true)

    async function fetchSimilar() {
      if (!selectedProductPost) return

      // Tier 1: If post has a catalog ID, query backend /api/v1/posts/{id} (same as Home page)
      if (!selectedProductPost.id.startsWith('post-user-') && !selectedProductPost.id.startsWith('share-')) {
        try {
          const products = await loadPostProducts(selectedProductPost.id)
          if (active && products.length > 0) {
            setSimilarProducts(products)
            setProductsAreDemo(false)
            setProductsLoading(false)
            return
          }
        } catch {
          // If 404 or backend unavailable for this post ID, proceed to visual AI search
        }
      }

      // Tier 2: If post has imageUrl, use FashionCLIP visual image search via /api/v1/search
      if (selectedProductPost.imageUrl) {
        try {
          const result = await searchCatalogProducts({
            queryImage: selectedProductPost.imageUrl,
            queryText: selectedProductPost.outfit?.name || selectedProductPost.caption || undefined,
            imageWeight: 0.7,
          })
          if (active && result.products.length > 0) {
            setSimilarProducts(result.products)
            setProductsAreDemo(false)
            setProductsLoading(false)
            return
          }
        } catch {
          // Proceed to demo fallback
        }
      }

      // Tier 3: Offline / local fallback
      if (active) {
        setSimilarProducts(demoProductsForPost(selectedProductPost))
        setProductsAreDemo(true)
        setProductsLoading(false)
      }
    }

    void fetchSimilar()

    return () => {
      active = false
    }
  }, [selectedProductPost])

  function navigate(
    page: AppPage,
  ) {
    if (!isAuthenticated && (page === 'profile' || page === 'post' || page === 'insights')) {
      setAuthDialogOpen(true)
      return
    }
    if (page === 'insights' && !isAdmin) {
      setNotice('只有公司管理員可以查看數據洞察')
      return
    }

    setCurrentPage(page)

    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    })
  }

  async function updateCurrentProfile(
    profile: Pick<User, 'displayName' | 'username' | 'bio' | 'avatarUrl'>,
  ) {
    const uid = activeUserId
    await savePublicProfile(uid, profile)
    if (currentUid.current !== uid) return
    setCurrentUser(current => ({ ...current, ...profile, avatarText: profile.displayName.slice(0, 1).toUpperCase() }))
    setNotice('個人檔案已更新')
  }

  async function signOutUser() {
    try { await signOutCurrentUser() } catch { setNotice('登出失敗，請重試'); return }
    setCurrentPage('home')
    setNotice('已登出帳號')
    setIsAdmin(false)
    setOnboardingOpen(false)
  }

  async function completeOnboarding(ageRange: AgeRange, styles: StyleOption[]) {
    await saveOnboardingProfile(onboardingUserId, { age_range: ageRange, preferred_styles: styles })
    setOnboardingOpen(false)
    setNotice('偏好已儲存，開始探索吧')
    await refreshFeed()
  }

  async function updatePostState(postId: string, field: 'liked' | 'saved') {
    if (!isAuthenticated) { setAuthDialogOpen(true); return }
    const uid = activeUserId
    const lock = `${uid}:${postId}:${field}`
    if (changingStates.current.has(lock)) return
    changingStates.current.add(lock)
    const ids = field === 'liked' ? likedIds : savedIds
    const value = !ids.includes(postId)
    try {
      await changePostState(uid, postId, field, value)
      if (currentUid.current !== uid) return
      const setter = field === 'liked' ? setLikedIds : setSavedIds
      setter(current => current.includes(postId) === value ? current : updateIdList(current, postId))
      setNotice(field === 'saved' ? (value ? '已收藏' : '已取消收藏') : (value ? '已按讚' : '已取消按讚'))
    } catch (error) {
      setNotice(error instanceof Error ? error.message : '儲存失敗，請重試')
    } finally { changingStates.current.delete(lock) }
  }
  function toggleLike(postId: string) { void updatePostState(postId, 'liked') }
  function toggleSave(postId: string) { void updatePostState(postId, 'saved') }

  function openProducts(
    post: OutfitPost,
  ) {
    productDwell.current = {
      activeFrom: document.visibilityState === 'visible' ? Date.now() : null,
      elapsedMs: 0,
    }
    if (isAuthenticated) {
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
    if (post && isAuthenticated) {
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
      if (isAuthenticated) {
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

  async function publishPost(draft: CreatePostDraft) {
    const uid = activeUserId
    await publishCloudPost(uid, draft.postId, draft.caption, draft.imageFile)
    if (currentUid.current !== uid) return
    setNotice('穿搭已發布')
    setAccountReload(value => value + 1)
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
          onShare={handleOpenShare}
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
          posts={accountPosts}
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
          onShare={handleOpenShare}
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
          posts={accountPosts}
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
          onShare={handleOpenShare}
          onUpdateProfile={updateCurrentProfile}
          onSignOut={signOutUser}
        />
      )
    }

    if (currentPage === 'insights') {
      return isAdmin ? <InsightsPage /> : null
    }

    return (
      <HomePage
        followedCreatorIds={followedCreatorIds}
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
        onImpression={recordImpression}
        onOpenProduct={openProduct}
        onShare={handleOpenShare}
      />
    )
  }

  return (
    <div className="social-app">
      <Toast
        message={notice}
      />

      <AuthDialog
        open={authDialogOpen}
        configured={authConfigured}
        onClose={() => setAuthDialogOpen(false)}
        onSuccess={setNotice}
      />

      <ShareOutfitDialog
        isOpen={Boolean(sharePost)}
        post={sharePost}
        friends={socialFriends}
        onClose={() => setSharePost(null)}
        onShareToFriend={handleShareToFriend}
        onNotify={setNotice}
      />

      <OnboardingDialog
        open={onboardingOpen}
        onComplete={completeOnboarding}
      />

      <div className="app-layout">
        <Sidebar
          currentPage={
            currentPage
          }
          currentUser={
            currentUser
          }
          isAuthenticated={isAuthenticated}
          isAdmin={isAdmin}
          onNavigate={
            navigate
          }
          onAuthClick={() => setAuthDialogOpen(true)}
          onSignOut={signOutUser}
        />

        <main className="main-column">
          {accountError && <div className="form-error" role="alert">{accountError} <button type="button" onClick={() => setAccountReload(value => value + 1)}>重新連線</button></div>}
          {!isAuthenticated && <button className="primary-button" type="button" onClick={() => setAuthDialogOpen(true)}>登入 / 註冊</button>}
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
          post={selectedProductPost}
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

import {
  Bookmark,
  BarChart3,
  Compass,
  Home,
  LogOut,
  Plus,
  ShoppingBag,
  User as UserIcon,
} from 'lucide-react'

import type {
  AppPage,
  User,
} from '../../types/index'

import { Avatar } from '../common/Avatar'

interface SidebarProps {
  currentPage: AppPage

  currentUser: User

  isAuthenticated: boolean
  isAdmin: boolean

  onNavigate: (page: AppPage) => void
  onAuthClick: () => void
  onSignOut: () => Promise<void>
}

const navigationItems: Array<{
  id: AppPage
  label: string
  icon: typeof Home
}> = [
  {
    id: 'shop',
    label: '商城',
    icon: ShoppingBag,
  },
  {
    id: 'home',
    label: '首頁',
    icon: Home,
  },
  {
    id: 'discover',
    label: '探索',
    icon: Compass,
  },
  {
    id: 'post',
    label: '發佈',
    icon: Plus,
  },
  {
    id: 'saved',
    label: '收藏',
    icon: Bookmark,
  },
  {
    id: 'profile',
    label: '我的',
    icon: UserIcon,
  },
]

export function Sidebar({
  currentPage,
  currentUser,
  isAuthenticated,
  isAdmin,
  onNavigate,
  onAuthClick,
  onSignOut,
}: SidebarProps) {
  return (
    <aside className="left-sidebar">
      <button
        className="brand"
        onClick={() => onNavigate('home')}
      >
        LOOP
      </button>

      <nav
        className="desktop-nav"
        aria-label="主要導覽"
      >
        {[...navigationItems, ...(isAdmin ? [{ id: 'insights' as AppPage, label: '數據洞察', icon: BarChart3 }] : [])].map(item => {
          const Icon = item.icon

          return (
            <button
              key={item.id}
              className={
                currentPage === item.id
                  ? 'nav-item active'
                  : 'nav-item'
              }
              onClick={() => onNavigate(item.id)}
            >
              <Icon
                size={22}
                strokeWidth={1.8}
              />

              <span>
                {item.label}
              </span>
            </button>
          )
        })}
      </nav>

      <button
        className="desktop-post-button"
        onClick={() => onNavigate('post')}
      >
        發佈穿搭
      </button>

      <div className="sidebar-account">
      <button
        className="mini-profile"
        onClick={() => isAuthenticated ? onNavigate('profile') : onAuthClick()}
      >
        <Avatar
          user={currentUser}
          size="small"
        />

        <span>
          <strong>
            {isAuthenticated ? currentUser.displayName : '登入 / 註冊'}
          </strong>

          <small>
            {isAuthenticated ? `@${currentUser.username}` : '同步收藏與偏好'}
          </small>
        </span>
      </button>
      {isAuthenticated && <button className="sidebar-signout" type="button" title="登出帳號" aria-label="登出帳號" onClick={() => void onSignOut()}><LogOut size={18} strokeWidth={1.8} /></button>}
      </div>
    </aside>
  )
}

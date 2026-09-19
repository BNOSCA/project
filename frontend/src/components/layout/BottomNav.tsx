import {
  Bookmark,
  Compass,
  Home,
  Plus,
  ShoppingBag,
  User,
} from 'lucide-react'

import type { AppPage } from '../../types/index'

interface BottomNavProps {
  currentPage: AppPage

  onNavigate: (page: AppPage) => void
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
    icon: User,
  },
]

export function BottomNav({
  currentPage,
  onNavigate,
}: BottomNavProps) {
  return (
    <nav
      className="mobile-bottom-nav"
      aria-label="手機主要導覽"
    >
      {navigationItems.map(item => {
        const Icon = item.icon

        return (
          <button
            key={item.id}
            type="button"
            className={
              currentPage === item.id
                ? 'active'
                : ''
            }
            onClick={() => onNavigate(item.id)}
          >
            <Icon size={22} />

            <span>
              {item.label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}

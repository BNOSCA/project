import {
  Bell,
  Search,
} from 'lucide-react'

interface MobileHeaderProps {
  onSearch: () => void
}

export function MobileHeader({
  onSearch,
}: MobileHeaderProps) {
  return (
    <header className="mobile-header">
      <strong>
        LOOP
      </strong>

      <div>
        <button
          type="button"
          aria-label="搜尋"
          onClick={onSearch}
        >
          <Search size={21} />
        </button>

        <button
          type="button"
          aria-label="通知"
        >
          <Bell size={21} />
        </button>
      </div>
    </header>
  )
}
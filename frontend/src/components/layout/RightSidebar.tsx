import {
  Search,
  Sparkles,
} from 'lucide-react'

interface RightSidebarProps {
  onDiscover: () => void
}

export function RightSidebar({
  onDiscover,
}: RightSidebarProps) {
  return (
    <aside className="right-sidebar">
      <button
        type="button"
        className="right-search"
        onClick={onDiscover}
      >
        <Search size={18} />

        <span>
          搜尋 LOOP
        </span>
      </button>

      <section className="side-card">
        <div className="side-title">
          <Sparkles size={17} />

          <strong>
            AI For You
          </strong>
        </div>

        <h2>
          你的風格正在形成。
        </h2>

        <p>
          最近你對 Minimal、
          Smart Casual 和中性色系
          的穿搭互動較多。
        </p>

        <div className="preference-tags">
          <span>
            Minimal 88%
          </span>

          <span>
            Smart Casual 74%
          </span>

          <span>
            Neutral 69%
          </span>
        </div>
      </section>

      <section className="side-card">
        <span className="side-label">
          TRENDING
        </span>

        <button
          type="button"
          onClick={onDiscover}
        >
          <strong>
            #summerfit
          </strong>

          <small>
            2.4K posts
          </small>
        </button>

        <button
          type="button"
          onClick={onDiscover}
        >
          <strong>
            #minimal
          </strong>

          <small>
            8.7K posts
          </small>
        </button>

        <button
          type="button"
          onClick={onDiscover}
        >
          <strong>
            #officewear
          </strong>

          <small>
            4.1K posts
          </small>
        </button>
      </section>

      <small className="side-footer">
        LOOP Demo · AI Fashion Social Platform
      </small>
    </aside>
  )
}
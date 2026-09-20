import { useEffect, useState } from 'react'

import { loadAdminInsights, type AdminInsights } from '../services/admin'

export function InsightsPage() {
  const [data, setData] = useState<AdminInsights | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    loadAdminInsights().then(setData).catch(() => setError('目前無法取得洞察資料。'))
  }, [])

  if (error) return <section className="insights-page"><div className="empty-state">{error}</div></section>
  if (!data) return <section className="insights-page"><div className="empty-state">載入洞察中...</div></section>

  const kpis = [
    ['使用者', data.overview.total_users ?? 0],
    ['近 7 天活躍', data.overview.active_users_7d ?? 0],
    ['使用工作階段', data.overview.total_sessions ?? 0],
    ['互動總數', data.overview.total_interactions ?? 0],
  ]

  return (
    <section className="insights-page">
      <div className="page-heading"><div className="eyebrow">COMPANY INSIGHTS</div><h1>數據洞察</h1><p>只顯示聚合後的產品使用狀況。</p></div>
      <div className="insights-kpis">{kpis.map(([label, value]) => <div className="insight-kpi" key={label as string}><span>{label}</span><strong>{value}</strong></div>)}</div>
      <div className="insights-grid">
        <InsightList title="年齡分布" values={data.age_distribution} />
        <InsightList title="熱門風格" values={data.style_distribution} />
        <InsightList title="使用行為" values={data.engagement} />
        <InsightList title="轉換率" values={data.rates} percent />
      </div>
    </section>
  )
}

function InsightList({ title, values, percent = false }: { title: string; values: Record<string, number>; percent?: boolean }) {
  return <section className="insight-panel"><h2>{title}</h2>{Object.entries(values).map(([label, value]) => <div className="insight-row" key={label}><span>{label}</span><strong>{percent ? `${(value * 100).toFixed(1)}%` : value}</strong></div>)}</section>
}

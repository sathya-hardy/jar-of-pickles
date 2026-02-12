import { useEffect, useState } from 'react'

interface MrrDataPoint {
  month: string
  mrr_amount: number
  paying_customers: number
  total_customers: number
  active_subscriptions: number
}

interface ArpuDataPoint {
  month: string
  arppu: number
}

const formatDollar = (value: number) =>
  `$${value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`

const formatDollarDecimal = (value: number) =>
  `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

export function SummaryCards() {
  const [mrrData, setMrrData] = useState<MrrDataPoint[]>([])
  const [arpuData, setArpuData] = useState<ArpuDataPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('api/mrr').then(r => r.json()),
      fetch('api/arpu').then(r => r.json()),
    ])
      .then(([mrrJson, arpuJson]) => {
        setMrrData(mrrJson.data)
        setArpuData(arpuJson.data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-24 mb-3"></div>
            <div className="h-8 bg-gray-200 rounded w-32"></div>
          </div>
        ))}
      </div>
    )
  }

  const latest = mrrData[mrrData.length - 1]
  const previous = mrrData.length >= 2 ? mrrData[mrrData.length - 2] : null
  const latestArpu = arpuData[arpuData.length - 1]

  const momGrowth = previous
    ? ((latest.mrr_amount - previous.mrr_amount) / previous.mrr_amount) * 100
    : 0

  const cards = [
    {
      label: 'Current MRR',
      value: latest ? formatDollar(latest.mrr_amount) : '—',
      color: 'text-indigo-600',
    },
    {
      label: 'MoM Growth',
      value: previous ? `${momGrowth >= 0 ? '+' : ''}${momGrowth.toFixed(1)}%` : '—',
      color: momGrowth >= 0 ? 'text-green-600' : 'text-red-600',
    },
    {
      label: 'Paying Customers',
      value: latest ? latest.paying_customers.toString() : '—',
      color: 'text-blue-600',
    },
    {
      label: 'ARPPU',
      value: latestArpu ? formatDollarDecimal(latestArpu.arppu) : '—',
      color: 'text-purple-600',
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
        >
          <p className="text-sm font-medium text-gray-500">{card.label}</p>
          <p className={`text-2xl font-bold mt-1 ${card.color}`}>{card.value}</p>
        </div>
      ))}
    </div>
  )
}

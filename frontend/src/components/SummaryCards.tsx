import { useEffect, useState } from 'react'
import { DollarSign, TrendingUp, Users, UsersRound, BarChart3, UserMinus } from 'lucide-react'

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

interface ChurnDataPoint {
  month: string
  churn_rate: number
}

const formatDollar = (value: number) =>
  `$${value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`

const formatDollarDecimal = (value: number) =>
  `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

export function SummaryCards() {
  const [mrrData, setMrrData] = useState<MrrDataPoint[]>([])
  const [arpuData, setArpuData] = useState<ArpuDataPoint[]>([])
  const [churnData, setChurnData] = useState<ChurnDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/mrr').then((r) => {
        if (!r.ok) throw new Error(`MRR API failed: HTTP ${r.status}`)
        return r.json()
      }),
      fetch('/api/arpu').then((r) => {
        if (!r.ok) throw new Error(`ARPU API failed: HTTP ${r.status}`)
        return r.json()
      }),
      fetch('/api/churn').then((r) => {
        if (!r.ok) throw new Error(`Churn API failed: HTTP ${r.status}`)
        return r.json()
      }),
    ])
      .then(([mrrJson, arpuJson, churnJson]) => {
        setMrrData(mrrJson.data)
        setArpuData(arpuJson.data)
        setChurnData(churnJson.data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="grid grid-cols-6 gap-3 h-full">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 p-4 animate-pulse transition-colors duration-200">
            <div className="h-3 bg-gray-200 dark:bg-slate-600 rounded w-20 mb-3"></div>
            <div className="h-6 bg-gray-200 dark:bg-slate-600 rounded w-28"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 h-full flex items-center">
        <p className="text-red-600 dark:text-red-400 text-sm font-medium">Failed to load: {error}</p>
      </div>
    )
  }

  const latest = mrrData[mrrData.length - 1]
  const previous = mrrData.length >= 2 ? mrrData[mrrData.length - 2] : null
  const latestArpu = arpuData[arpuData.length - 1]
  const latestChurn = churnData[churnData.length - 1]

  const momGrowth =
    previous && previous.mrr_amount > 0
      ? ((latest.mrr_amount - previous.mrr_amount) / previous.mrr_amount) * 100
      : null

  const churnRate = latestChurn ? latestChurn.churn_rate : null

  const cards = [
    {
      label: 'Current MRR',
      value: latest ? formatDollar(latest.mrr_amount) : '\u2014',
      icon: DollarSign,
      iconColor: 'text-indigo-600 dark:text-indigo-400',
      iconBg: 'bg-indigo-50 dark:bg-indigo-900/30',
    },
    {
      label: 'MoM Growth',
      value: momGrowth !== null
        ? `${momGrowth >= 0 ? '+' : ''}${momGrowth.toFixed(1)}%`
        : '\u2014',
      icon: TrendingUp,
      iconColor: momGrowth !== null && momGrowth >= 0
        ? 'text-emerald-600 dark:text-emerald-400'
        : 'text-red-600 dark:text-red-400',
      iconBg: momGrowth !== null && momGrowth >= 0
        ? 'bg-emerald-50 dark:bg-emerald-900/30'
        : 'bg-red-50 dark:bg-red-900/30',
      valueColor: momGrowth !== null && momGrowth >= 0
        ? 'text-emerald-600 dark:text-emerald-400'
        : momGrowth !== null
          ? 'text-red-600 dark:text-red-400'
          : undefined,
    },
    {
      label: 'Paying Customers',
      value: latest ? latest.paying_customers.toString() : '\u2014',
      icon: Users,
      iconColor: 'text-sky-600 dark:text-sky-400',
      iconBg: 'bg-sky-50 dark:bg-sky-900/30',
    },
    {
      label: 'Total Customers',
      value: latest ? latest.total_customers.toString() : '\u2014',
      icon: UsersRound,
      iconColor: 'text-violet-600 dark:text-violet-400',
      iconBg: 'bg-violet-50 dark:bg-violet-900/30',
    },
    {
      label: 'ARPPU',
      value: latestArpu ? formatDollarDecimal(latestArpu.arppu) : '\u2014',
      icon: BarChart3,
      iconColor: 'text-teal-600 dark:text-teal-400',
      iconBg: 'bg-teal-50 dark:bg-teal-900/30',
    },
    {
      label: 'Churn Rate',
      value: churnRate !== null ? `${churnRate.toFixed(1)}%` : '\u2014',
      icon: UserMinus,
      iconColor: churnRate !== null && churnRate > 0
        ? 'text-red-600 dark:text-red-400'
        : 'text-emerald-600 dark:text-emerald-400',
      iconBg: churnRate !== null && churnRate > 0
        ? 'bg-red-50 dark:bg-red-900/30'
        : 'bg-emerald-50 dark:bg-emerald-900/30',
      valueColor: churnRate !== null && churnRate > 0
        ? 'text-red-600 dark:text-red-400'
        : churnRate !== null
          ? 'text-emerald-600 dark:text-emerald-400'
          : undefined,
    },
  ]

  return (
    <div className="grid grid-cols-6 gap-3 h-full">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <div
            key={card.label}
            className="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 p-3 flex items-center gap-2.5 transition-colors duration-200"
          >
            <div className={`p-1.5 rounded-lg ${card.iconBg} transition-colors duration-200`}>
              <Icon className={`w-4 h-4 ${card.iconColor}`} />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-gray-500 dark:text-slate-400 truncate">{card.label}</p>
              <p className={`text-lg font-bold ${card.valueColor || 'text-gray-900 dark:text-white'} transition-colors duration-200`}>
                {card.value}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

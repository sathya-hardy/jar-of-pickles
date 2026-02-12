import { useEffect, useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface RawDataPoint {
  month: string
  plan_name: string
  mrr_amount: number
}

interface ChartDataPoint {
  month: string
  Free: number
  Standard: number
  'Pro Plus': number
  Engage: number
  Enterprise: number
}

const PLAN_COLORS: Record<string, string> = {
  'Free': '#94a3b8',
  'Standard': '#60a5fa',
  'Pro Plus': '#a78bfa',
  'Engage': '#f472b6',
  'Enterprise': '#fb923c',
}

const PLAN_ORDER = ['Free', 'Standard', 'Pro Plus', 'Engage', 'Enterprise']

const formatDollar = (value: number) =>
  `$${(value / 1000).toFixed(0)}k`

export function PlanBreakdown() {
  const [data, setData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/mrr-by-plan')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((json) => {
        // Pivot: group by month, with plan names as columns
        const byMonth: Record<string, ChartDataPoint> = {}
        json.data.forEach((row: RawDataPoint) => {
          if (!byMonth[row.month]) {
            byMonth[row.month] = {
              month: row.month,
              Free: 0,
              Standard: 0,
              'Pro Plus': 0,
              Engage: 0,
              Enterprise: 0,
            }
          }
          const key = row.plan_name as keyof ChartDataPoint
          if (key in byMonth[row.month]) {
            (byMonth[row.month][key] as number) = row.mrr_amount
          }
        })
        setData(Object.values(byMonth).sort((a, b) => a.month.localeCompare(b.month)))
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) return <div className="h-72 flex items-center justify-center text-gray-400">Loading...</div>
  if (error) return <div className="h-72 flex items-center justify-center text-red-500">Error: {error}</div>
  if (data.length === 0) return <div className="h-72 flex items-center justify-center text-gray-400">No data</div>

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="month" tick={{ fontSize: 12 }} />
        <YAxis tickFormatter={formatDollar} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(value: number) => [`$${value.toLocaleString()}`, '']} />
        <Legend />
        {PLAN_ORDER.map((plan) => (
          <Area
            key={plan}
            type="monotone"
            dataKey={plan}
            stackId="1"
            stroke={PLAN_COLORS[plan]}
            fill={PLAN_COLORS[plan]}
            fillOpacity={0.6}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}

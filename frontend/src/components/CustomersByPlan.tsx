import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
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
  customer_count: number
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

export function CustomersByPlan() {
  const [data, setData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/customers-by-plan')
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
            (byMonth[row.month][key] as number) = row.customer_count
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
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="month" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        {PLAN_ORDER.map((plan) => (
          <Bar
            key={plan}
            dataKey={plan}
            stackId="1"
            fill={PLAN_COLORS[plan]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
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

interface CustomersByPlanProps {
  isDarkMode: boolean
}

const PLAN_COLORS_LIGHT: Record<string, string> = {
  'Free': '#808e71',       // dusty-olive 500
  'Standard': '#4e76b1',   // yale-blue 500
  'Pro Plus': '#a92523',    // dark-wine 600
  'Engage': '#c76605',      // sandy-brown 600
  'Enterprise': '#2ba15a',  // celadon 600
}

const PLAN_COLORS_DARK: Record<string, string> = {
  'Free': '#ccd2c6',       // dusty-olive 200
  'Standard': '#7191c1',   // yale-blue 400
  'Pro Plus': '#dc5856',    // dark-wine 400
  'Engage': '#fa9938',      // sandy-brown 400
  'Enterprise': '#5ed48d',  // celadon 400
}

const PLAN_ORDER = ['Free', 'Standard', 'Pro Plus', 'Engage', 'Enterprise']

export function CustomersByPlan({ isDarkMode }: CustomersByPlanProps) {
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

  const colors = isDarkMode ? PLAN_COLORS_DARK : PLAN_COLORS_LIGHT
  const gridColor = isDarkMode ? '#334155' : '#e5e7eb'
  const textColor = isDarkMode ? '#94a3b8' : '#6b7280'

  if (loading) return <div className="h-full flex items-center justify-center text-gray-400 dark:text-slate-500">Loading...</div>
  if (error) return <div className="h-full flex items-center justify-center text-red-500 dark:text-red-400 text-sm">Error: {error}</div>
  if (data.length === 0) return <div className="h-full flex items-center justify-center text-gray-400 dark:text-slate-500">No data</div>

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid horizontal={true} vertical={false} strokeDasharray="3 3" stroke={gridColor} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: textColor }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11, fill: textColor }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{
            borderRadius: '8px',
            border: isDarkMode ? '1px solid #334155' : '1px solid #e5e7eb',
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            color: isDarkMode ? '#e2e8f0' : '#1f2937',
          }}
          labelStyle={{ color: isDarkMode ? '#94a3b8' : '#6b7280' }}
        />
        <Legend
          wrapperStyle={{ fontSize: '11px', color: isDarkMode ? '#94a3b8' : '#6b7280' }}
        />
        {PLAN_ORDER.map((plan, i) => (
          <Bar
            key={plan}
            dataKey={plan}
            stackId="a"
            fill={colors[plan]}
            radius={i === PLAN_ORDER.length - 1 ? [4, 4, 0, 0] : undefined}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

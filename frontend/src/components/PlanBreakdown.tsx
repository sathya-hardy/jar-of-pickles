import { useEffect, useState } from 'react'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface RawDataPoint {
  month: string
  plan_name: string
  mrr_amount: number
}

interface PieDataPoint {
  name: string
  value: number
}

interface PlanBreakdownProps {
  isDarkMode: boolean
}

const PLAN_COLORS_LIGHT: Record<string, string> = {
  'Free': '#9ca3af',
  'Standard': '#f59e0b',
  'Pro Plus': '#ef4444',
  'Engage': '#d946ef',
  'Enterprise': '#1e293b',
}

const PLAN_COLORS_DARK: Record<string, string> = {
  'Free': '#9ca3af',
  'Standard': '#fbbf24',
  'Pro Plus': '#f87171',
  'Engage': '#e879f9',
  'Enterprise': '#e2e8f0',
}

const PLAN_ORDER = ['Free', 'Standard', 'Pro Plus', 'Engage', 'Enterprise']

export function PlanBreakdown({ isDarkMode }: PlanBreakdownProps) {
  const [data, setData] = useState<PieDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/mrr-by-plan')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((json) => {
        // Get the latest month's data for the pie chart
        const rows = json.data as RawDataPoint[]
        if (rows.length === 0) {
          setData([])
          setLoading(false)
          return
        }
        const latestMonth = rows[rows.length - 1].month
        const latestData = rows.filter((r) => r.month === latestMonth)

        const pieData: PieDataPoint[] = PLAN_ORDER
          .map((plan) => {
            const match = latestData.find((r) => r.plan_name === plan)
            return { name: plan, value: match ? match.mrr_amount : 0 }
          })
          .filter((d) => d.value > 0)

        setData(pieData)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const colors = isDarkMode ? PLAN_COLORS_DARK : PLAN_COLORS_LIGHT

  if (loading) return <div className="h-full flex items-center justify-center text-gray-400 dark:text-slate-500">Loading...</div>
  if (error) return <div className="h-full flex items-center justify-center text-red-500 dark:text-red-400 text-sm">Error: {error}</div>
  if (data.length === 0) return <div className="h-full flex items-center justify-center text-gray-400 dark:text-slate-500">No data</div>

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="45%"
          innerRadius="60%"
          outerRadius="80%"
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((entry) => (
            <Cell key={entry.name} fill={colors[entry.name] || '#94a3b8'} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
          contentStyle={{
            borderRadius: '8px',
            border: isDarkMode ? '1px solid #334155' : '1px solid #e5e7eb',
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            color: isDarkMode ? '#e2e8f0' : '#1f2937',
          }}
          itemStyle={{ color: isDarkMode ? '#e2e8f0' : '#1f2937' }}
          labelStyle={{ color: isDarkMode ? '#94a3b8' : '#6b7280' }}
        />
        <Legend
          verticalAlign="bottom"
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: '11px', color: isDarkMode ? '#94a3b8' : '#6b7280' }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

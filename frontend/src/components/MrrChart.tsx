import { useEffect, useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface MrrDataPoint {
  month: string
  mrr_amount: number
}

interface MrrChartProps {
  isDarkMode: boolean
}

const formatDollar = (value: number) =>
  `$${(value / 1000).toFixed(0)}k`

const formatDollarFull = (value: number) =>
  `$${value.toLocaleString('en-US', { minimumFractionDigits: 0 })}`

export function MrrChart({ isDarkMode }: MrrChartProps) {
  const [data, setData] = useState<MrrDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/mrr')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((json) => {
        setData(json.data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const strokeColor = isDarkMode ? '#4ade80' : '#15803d'
  const gridColor = isDarkMode ? '#334155' : '#e5e7eb'
  const textColor = isDarkMode ? '#94a3b8' : '#6b7280'

  if (loading) return <div className="h-full flex items-center justify-center text-gray-400 dark:text-slate-500">Loading...</div>
  if (error) return <div className="h-full flex items-center justify-center text-red-500 dark:text-red-400 text-sm">Error: {error}</div>
  if (data.length === 0) return <div className="h-full flex items-center justify-center text-gray-400 dark:text-slate-500">No data</div>

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="mrrGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={strokeColor} stopOpacity={0.3} />
            <stop offset="95%" stopColor={strokeColor} stopOpacity={0.0} />
          </linearGradient>
        </defs>
        <CartesianGrid horizontal={true} vertical={false} strokeDasharray="3 3" stroke={gridColor} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: textColor }} tickLine={false} axisLine={false} />
        <YAxis tickFormatter={formatDollar} tick={{ fontSize: 11, fill: textColor }} tickLine={false} axisLine={false} />
        <Tooltip
          formatter={(value: number) => [formatDollarFull(value), 'MRR']}
          contentStyle={{
            borderRadius: '8px',
            border: isDarkMode ? '1px solid #334155' : '1px solid #e5e7eb',
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            color: isDarkMode ? '#e2e8f0' : '#1f2937',
          }}
          labelStyle={{ color: isDarkMode ? '#94a3b8' : '#6b7280' }}
        />
        <Area
          type="monotone"
          dataKey="mrr_amount"
          stroke={strokeColor}
          strokeWidth={2}
          fill="url(#mrrGradient)"
          dot={{ r: 4, fill: strokeColor, stroke: strokeColor }}
          activeDot={{ r: 6, fill: strokeColor }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

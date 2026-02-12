import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface ArpuDataPoint {
  month: string
  arppu: number
}

interface ArpuChartProps {
  isDarkMode: boolean
}

export function ArpuChart({ isDarkMode }: ArpuChartProps) {
  const [data, setData] = useState<ArpuDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/arpu')
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

  const strokeColor = isDarkMode ? '#2dd4bf' : '#0d9488'
  const gridColor = isDarkMode ? '#334155' : '#e5e7eb'
  const textColor = isDarkMode ? '#94a3b8' : '#6b7280'

  if (loading) return <div className="h-full flex items-center justify-center text-gray-400 dark:text-slate-500">Loading...</div>
  if (error) return <div className="h-full flex items-center justify-center text-red-500 dark:text-red-400 text-sm">Error: {error}</div>
  if (data.length === 0) return <div className="h-full flex items-center justify-center text-gray-400 dark:text-slate-500">No data</div>

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid horizontal={true} vertical={false} strokeDasharray="3 3" stroke={gridColor} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: textColor }} tickLine={false} axisLine={false} />
        <YAxis
          tickFormatter={(value: number) => `$${value.toFixed(0)}`}
          tick={{ fontSize: 11, fill: textColor }}
          tickLine={false}
          axisLine={false}
          domain={['dataMin - 2', 'dataMax + 2']}
        />
        <Tooltip
          formatter={(value: number) => [`$${value.toFixed(2)}`, 'ARPPU']}
          contentStyle={{
            borderRadius: '8px',
            border: isDarkMode ? '1px solid #334155' : '1px solid #e5e7eb',
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            color: isDarkMode ? '#e2e8f0' : '#1f2937',
          }}
          labelStyle={{ color: isDarkMode ? '#94a3b8' : '#6b7280' }}
        />
        <Line
          type="monotone"
          dataKey="arppu"
          stroke={strokeColor}
          strokeWidth={2}
          dot={{ r: 4, fill: strokeColor, stroke: strokeColor }}
          activeDot={{ r: 6, fill: strokeColor }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

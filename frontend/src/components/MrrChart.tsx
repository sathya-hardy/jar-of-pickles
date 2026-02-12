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

interface MrrDataPoint {
  month: string
  mrr_amount: number
}

const formatDollar = (value: number) =>
  `$${(value / 1000).toFixed(0)}k`

const formatDollarFull = (value: number) =>
  `$${value.toLocaleString('en-US', { minimumFractionDigits: 0 })}`

export function MrrChart() {
  const [data, setData] = useState<MrrDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('api/mrr')
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

  if (loading) return <div className="h-72 flex items-center justify-center text-gray-400">Loading...</div>
  if (error) return <div className="h-72 flex items-center justify-center text-red-500">Error: {error}</div>
  if (data.length === 0) return <div className="h-72 flex items-center justify-center text-gray-400">No data</div>

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="month" tick={{ fontSize: 12 }} />
        <YAxis tickFormatter={formatDollar} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(value: number) => [formatDollarFull(value), 'MRR']} />
        <Line
          type="monotone"
          dataKey="mrr_amount"
          stroke="#6366f1"
          strokeWidth={2}
          dot={{ r: 4, fill: '#6366f1' }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

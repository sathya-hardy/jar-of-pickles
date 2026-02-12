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

const formatDollar = (value: number) =>
  `$${value.toFixed(0)}`

export function ArpuChart() {
  const [data, setData] = useState<ArpuDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('api/arpu')
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
        <Tooltip formatter={(value: number) => [`$${value.toFixed(2)}`, 'ARPPU']} />
        <Line
          type="monotone"
          dataKey="arppu"
          stroke="#8b5cf6"
          strokeWidth={2}
          dot={{ r: 4, fill: '#8b5cf6' }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

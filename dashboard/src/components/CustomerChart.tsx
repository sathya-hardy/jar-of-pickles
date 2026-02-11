import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface MrrDataPoint {
  month: string
  paying_customers: number
  total_customers: number
}

export function CustomerChart() {
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
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="total_customers"
          stroke="#94a3b8"
          strokeWidth={2}
          name="Total Customers"
          dot={{ r: 3 }}
        />
        <Line
          type="monotone"
          dataKey="paying_customers"
          stroke="#3b82f6"
          strokeWidth={2}
          name="Paying Customers"
          dot={{ r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

import { SummaryCards } from './components/SummaryCards'
import { MrrChart } from './components/MrrChart'
import { PlanBreakdown } from './components/PlanBreakdown'
import { ArpuChart } from './components/ArpuChart'
import { CustomerChart } from './components/CustomerChart'

function App() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          MRR Dashboard
        </h1>
        <p className="text-gray-500 mb-8">
          Monthly Recurring Revenue &mdash; Digital Signage SaaS
        </p>

        {/* Summary Cards */}
        <SummaryCards />

        {/* MRR Trend + Plan Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">MRR Trend</h2>
            <MrrChart />
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Revenue by Plan</h2>
            <PlanBreakdown />
          </div>
        </div>

        {/* ARPPU + Customer Count */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">ARPPU Trend</h2>
            <ArpuChart />
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Customer Count</h2>
            <CustomerChart />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

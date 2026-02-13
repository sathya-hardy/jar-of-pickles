import { useState } from 'react'
import { LayoutDashboard, Sun, Moon } from 'lucide-react'
import { SummaryCards } from './components/SummaryCards'
import { MrrChart } from './components/MrrChart'
import { PlanBreakdown } from './components/PlanBreakdown'
import { ArpuChart } from './components/ArpuChart'
import { CustomerChart } from './components/CustomerChart'
import { CustomersByPlan } from './components/CustomersByPlan'

function App() {
  const [isDarkMode, setIsDarkMode] = useState(false)

  return (
    <div className={`${isDarkMode ? 'dark' : ''}`}>
      <div className="min-h-screen w-screen overflow-auto lg:h-screen lg:overflow-hidden flex flex-col bg-gray-50 dark:bg-slate-900 transition-colors duration-200">
        {/* Header */}
        <header className="flex items-center justify-between px-4 lg:px-6 py-3 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 transition-colors duration-200">
          <div className="flex items-center gap-3">
            <LayoutDashboard className="w-6 h-6 text-green-700 dark:text-green-400" />
            <div>
              <h1 className="text-base lg:text-lg font-bold text-gray-900 dark:text-white leading-tight">
                MRR Dashboard
              </h1>
              <p className="text-xs text-gray-500 dark:text-slate-400 hidden sm:block">
                Monthly Recurring Revenue &mdash; Digital Signage SaaS
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 lg:gap-4">
            <span className="text-xs text-gray-400 dark:text-slate-500 hidden sm:inline">Last 7 months</span>
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors duration-200"
              aria-label="Toggle dark mode"
            >
              {isDarkMode ? (
                <Sun className="w-5 h-5 text-slate-400" />
              ) : (
                <Moon className="w-5 h-5 text-gray-500" />
              )}
            </button>
          </div>
        </header>

        {/* Body */}
        <div className="flex-1 flex flex-col p-3 lg:p-4 gap-3 lg:gap-4 lg:min-h-0">
          {/* Summary Cards */}
          <div className="shrink-0 lg:h-28">
            <SummaryCards />
          </div>

          {/* Top chart row: MRR Trend (2/3) + Revenue by Plan (1/3) */}
          <div className="flex flex-col lg:flex-row lg:flex-1 gap-3 lg:gap-4 lg:min-h-0">
            <div className="h-72 lg:h-auto lg:flex-[2] min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 p-4 flex flex-col transition-colors duration-200">
              <h2 className="text-sm font-semibold text-gray-800 dark:text-slate-100 mb-2">MRR Trend</h2>
              <div className="flex-1 min-h-0">
                <MrrChart isDarkMode={isDarkMode} />
              </div>
            </div>
            <div className="h-72 lg:h-auto lg:flex-[1] min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 p-4 flex flex-col transition-colors duration-200">
              <h2 className="text-sm font-semibold text-gray-800 dark:text-slate-100 mb-2">Revenue by Plan</h2>
              <div className="flex-1 min-h-0">
                <PlanBreakdown isDarkMode={isDarkMode} />
              </div>
            </div>
          </div>

          {/* Bottom chart row: ARPPU (1/3) + Customers (1/3) + Customers by Plan (1/3) */}
          <div className="flex flex-col lg:flex-row lg:flex-1 gap-3 lg:gap-4 lg:min-h-0">
            <div className="h-72 lg:h-auto lg:flex-1 min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 p-4 flex flex-col transition-colors duration-200">
              <h2 className="text-sm font-semibold text-gray-800 dark:text-slate-100 mb-2">ARPPU Trend</h2>
              <div className="flex-1 min-h-0">
                <ArpuChart isDarkMode={isDarkMode} />
              </div>
            </div>
            <div className="h-72 lg:h-auto lg:flex-1 min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 p-4 flex flex-col transition-colors duration-200">
              <h2 className="text-sm font-semibold text-gray-800 dark:text-slate-100 mb-2">Active Customers</h2>
              <div className="flex-1 min-h-0">
                <CustomerChart isDarkMode={isDarkMode} />
              </div>
            </div>
            <div className="h-72 lg:h-auto lg:flex-1 min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 p-4 flex flex-col transition-colors duration-200">
              <h2 className="text-sm font-semibold text-gray-800 dark:text-slate-100 mb-2">Customers by Plan</h2>
              <div className="flex-1 min-h-0">
                <CustomersByPlan isDarkMode={isDarkMode} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

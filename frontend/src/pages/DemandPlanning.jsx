import React, { useState } from 'react'
import { optimizationService } from '../services/optimizationService'
import { FileText, Download, TrendingUp, AlertCircle } from 'lucide-react'
import './Dashboard.css'

const DemandPlanning = () => {
  const [loading, setLoading] = useState(false)
  const [storeId, setStoreId] = useState('11')
  const [productId, setProductId] = useState('267')
  const [timeRange, setTimeRange] = useState('7d')

  const handleDownloadReport = async () => {
    if (!storeId || !productId) {
      alert("Please enter Store ID and Product ID")
      return
    }

    setLoading(true)
    try {
      const payload = {
        time_range: timeRange,
        store_id: Number(storeId),
        product_ids: [Number(productId)],
        constraints: { budget: 50000000, max_inventory: 50000000, lead_time: 7 } // Defaults
      }

      const blob = await optimizationService.generateReport(payload)

      // Create download link
      const url = window.URL.createObjectURL(new Blob([blob]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Decision_Report_Store${storeId}_Product${productId}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.parentNode.removeChild(link)
      window.URL.revokeObjectURL(url)

    } catch (err) {
      console.error(err)
      alert('Error generating report: ' + (err?.message || 'Check Backend Logs'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-8">
        <h2 className="text-2xl font-bold flex items-center text-gray-800">
          <FileText className="mr-2 text-blue-600" />
          Demand Planning & Decision Report
        </h2>
        <p className="text-gray-500 mt-1">
          Generate comprehensive PDF reports comparing strategies, analyzing costs, and providing AI-driven recommendations.
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-md p-8 border border-gray-100">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Store ID</label>
            <input
              type="number"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="e.g. 11"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Product ID</label>
            <input
              type="number"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="e.g. 267"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Time Horizon</label>
            <select
              value={timeRange}
              readOnly
              className="w-full p-2 border border-gray-300 rounded-md bg-gray-100 cursor-not-allowed outline-none"
            >
              <option value="7d">Next 7 Days (Fixed)</option>
            </select>
          </div>
        </div>

        <div className="flex flex-col items-center justify-center py-6 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
          <div className="text-center mb-6 max-w-md">
            <TrendingUp className="mx-auto h-12 w-12 text-blue-500 mb-3" />
            <h3 className="text-lg font-semibold text-gray-800">Ready to Generate</h3>
            <p className="text-gray-500 text-sm">
              The report will run simulations for Rule-Based, Math-Based, and AI-DDMRP strategies using your current forecast data.
            </p>
          </div>

          <button
            onClick={handleDownloadReport}
            disabled={loading}
            className={`flex items-center px-8 py-3 text-white rounded-lg shadow-lg transition-all transform hover:scale-105 ${loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700'
              }`}
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Generating Analysis...
              </>
            ) : (
              <>
                <Download className="mr-2 h-5 w-5" />
                Generate & Download PDF Report
              </>
            )}
          </button>
        </div>

        <div className="mt-6 flex items-start p-4 bg-blue-50 text-blue-800 rounded-md text-sm">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
          <p>
            Note: Ensure your Forecast CSV (final_forecast.csv) is up-to-date.
            The report generation process may take 10-20 seconds to run all simulations.
          </p>
        </div>
      </div>
    </div>
  )
}

export default DemandPlanning
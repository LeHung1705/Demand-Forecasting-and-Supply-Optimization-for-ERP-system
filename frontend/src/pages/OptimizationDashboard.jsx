import React, { useState } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import {
  TrendingUp,
  ShoppingCart,
  AlertCircle,
  CheckCircle,
  Package,
  Activity,
  Settings
} from 'lucide-react';
import api from '../services/api';

const OptimizationDashboard = () => {
  // State
  const [storeId, setStoreId] = useState(11);
  const [productId, setProductId] = useState(267);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Handlers
  const handleRunOptimization = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Hardcoded params as per "Hidden Params" requirement
      const payload = {
        store_id: Number(storeId),
        product_id: Number(productId),
        strategy_type: 'AI-DDMRP',
        params: {
          lead_time: 1,
          service_level: 0.95,
          holding_cost: 1.0,
          shortage_cost: 100.0
        }
      };

      const res = await api.post('/api/v1/optimize/simulate', payload);
      setResult(res);
    } catch (err) {
      console.error(err);
      setError('Simulation failed to run. Please check Store/Product IDs.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePO = () => {
    alert(`Purchase Order Created for SKU ${result.recommendation.sku} with Qty: ${result.recommendation.order_qty}`);
  };

  // Chart Data Preparation
  const chartData = result ? result.charts.dates.map((date, i) => ({
    name: date,
    inventory: result.charts.inventory[i],
    demand: result.charts.demand[i],
    forecast: result.charts.forecast[i],
    baseline: result.charts.baseline_inventory[i]
  })) : [];

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 font-sans p-6">
      {/* HEADER */}
      <header className="mb-8 flex flex-col md:flex-row justify-between items-center gap-4 border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2 text-white">
            <Activity className="text-blue-500" />
            Supply Chain Command Center
          </h1>
          <p className="text-gray-400 text-sm mt-1">AI-Driven Demand Driven MRP Engine</p>
        </div>

        {/* INPUT BAR */}
        <div className="flex items-center gap-3 bg-gray-800 p-2 rounded-lg border border-gray-700">
          <div className="flex flex-col">
            <label className="text-xs text-gray-500 font-semibold px-1">Store ID</label>
            <input
              type="number"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              className="bg-transparent text-white font-mono w-20 px-2 py-1 focus:outline-none border-b border-gray-600 focus:border-blue-500"
            />
          </div>
          <div className="w-px h-8 bg-gray-700"></div>
          <div className="flex flex-col">
            <label className="text-xs text-gray-500 font-semibold px-1">Product ID</label>
            <input
              type="number"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              className="bg-transparent text-white font-mono w-24 px-2 py-1 focus:outline-none border-b border-gray-600 focus:border-blue-500"
            />
          </div>
          <button
            onClick={handleRunOptimization}
            disabled={loading}
            className={`ml-4 px-6 py-3 rounded-md font-bold text-sm tracking-wide transition-all shadow-lg
              ${loading
                ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-500 text-white hover:shadow-blue-500/20'}`}
          >
            {loading ? 'ANALYZING...' : 'RUN OPTIMIZATION'}
          </button>
        </div>
      </header>

      {/* ERROR STATE */}
      {error && (
        <div className="bg-red-900/20 border border-red-800 text-red-200 p-4 rounded-lg mb-6 flex items-center gap-3">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      {/* DASHBOARD CONTENT */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in duration-500">

          {/* LEFT: HERO RECOMMENDATION CARD */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <ShoppingCart size={120} />
              </div>

              <h3 className="text-gray-400 font-medium uppercase tracking-wider text-xs mb-2">Recommendation</h3>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-5xl font-extrabold text-blue-400">{result.recommendation.order_qty}</span>
                <span className="text-xl text-gray-500">units</span>
              </div>
              <p className="text-gray-300 mt-2 font-medium">Suggested Restock Order</p>

              <div className="mt-8 space-y-3">
                <div className="flex justify-between items-center p-3 bg-gray-900/50 rounded-lg">
                  <span className="text-gray-400 text-sm">Projected Profit</span>
                  <span className="text-green-400 font-mono font-bold">
                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(result.recommendation.projected_profit)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-900/50 rounded-lg">
                  <span className="text-gray-400 text-sm">Fill Rate Target</span>
                  <span className="text-blue-300 font-mono font-bold">{result.recommendation.fill_rate}%</span>
                </div>
              </div>

              <button
                onClick={handleCreatePO}
                className="w-full mt-6 bg-green-600 hover:bg-green-500 text-white font-bold py-4 rounded-lg flex items-center justify-center gap-2 transition-transform active:scale-95 shadow-lg shadow-green-900/20"
              >
                <CheckCircle size={20} />
                CREATE PURCHASE ORDER
              </button>
            </div>

            {/* COMPARISON MINI-CARD */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-xl">
              <h3 className="text-gray-400 font-medium uppercase tracking-wider text-xs mb-4 flex items-center gap-2">
                <TrendingUp size={16} /> Strategy Comparison
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-white">AI-DDMRP</span>
                    <span className="text-green-400 font-bold">
                      {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(result.comparison.ai_profit)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-700 h-2 rounded-full overflow-hidden">
                    <div className="bg-green-500 h-full" style={{ width: '100%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-400">Rule-Based</span>
                    <span className="text-gray-400">
                      {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(result.comparison.rule_based_profit)}
                    </span>
                  </div>
                  {/* Width calculation is approximate for visual demo */}
                  <div className="w-full bg-gray-700 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-gray-500 h-full"
                      style={{ width: `${Math.min(100, (result.comparison.rule_based_profit / result.comparison.ai_profit) * 100)}%` }}
                    ></div>
                  </div>
                </div>

                <div className="pt-2 text-xs text-center text-gray-500">
                  AI Strategy improved profit by <span className="text-green-400 font-bold">
                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(result.comparison.improvement)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: VISUALIZATION CHART */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-xl h-full flex flex-col">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-white font-bold text-lg flex items-center gap-2">
                  <Package size={20} className="text-purple-500" />
                  Inventory Simulation (Next 7 Days)
                </h3>
                <div className="flex gap-4 text-xs font-medium">
                  <span className="flex items-center gap-1 text-gray-400"><div className="w-3 h-3 bg-green-500/20 border border-green-500 rounded-sm"></div> AI Inventory</span>
                  <span className="flex items-center gap-1 text-gray-400"><div className="w-3 h-3 bg-orange-500 rounded-full"></div> Demand</span>
                </div>
              </div>

              <div className="flex-1 w-full min-h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorInv" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                    <XAxis
                      dataKey="name"
                      stroke="#9ca3af"
                      tick={{ fill: '#9ca3af', fontSize: 12 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="#9ca3af"
                      tick={{ fill: '#9ca3af', fontSize: 12 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                      itemStyle={{ color: '#f3f4f6' }}
                      cursor={{ stroke: '#4b5563' }}
                    />
                    <Legend />
                    {/* Areas and Lines */}
                    <Area
                      type="monotone"
                      dataKey="inventory"
                      name="AI Inventory Level"
                      stroke="#10b981"
                      fillOpacity={1}
                      fill="url(#colorInv)"
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="demand"
                      name="Daily Demand"
                      stroke="#f97316"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="baseline"
                      name="Rule-Based (Legacy)"
                      stroke="#6b7280"
                      strokeDasharray="5 5"
                      strokeWidth={1}
                      dot={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

        </div>
      )}

      {/* EMPTY STATE */}
      {!result && !loading && !error && (
        <div className="flex flex-col items-center justify-center h-[60vh] text-gray-500 animate-in fade-in zoom-in duration-500">
          <div className="bg-gray-800 p-8 rounded-full mb-6 shadow-2xl shadow-blue-900/20">
            <Activity size={64} className="text-gray-600" />
          </div>
          <h2 className="text-xl font-medium text-gray-400">Ready to Optimize</h2>
          <p className="max-w-md text-center mt-2 text-gray-500">
            Enter a Store ID and Product ID above, then click "Run Optimization" to generate AI-driven replenishment suggestions from real data.
          </p>
        </div>
      )}
    </div>
  );
};

export default OptimizationDashboard;
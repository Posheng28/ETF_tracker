import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, TrendingDown, Layers, Activity, Calendar, DollarSign } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

const formatCurrency = (val) => {
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    maximumFractionDigits: 0
  }).format(val);
};

const formatNumber = (val) => {
  return new Intl.NumberFormat('zh-TW').format(val);
};

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('aggregated');
  const [sortConfig, setSortConfig] = useState({ key: 'monetary_value', direction: 'desc' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/holdings/changes`);
      setData(res.data);
    } catch (err) {
      console.error("Failed to fetch data", err);
    } finally {
      setLoading(false);
    }
  };

  const requestSort = (key) => {
    let direction = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  const getSortedData = (type = 'changes') => {
    if (!data) return [];

    let items = [];
    if (activeTab === 'aggregated') {
      // FIX: Aggregated view must be calculated on frontend because backend delivers etf_details
      if (type === 'changes') {
        Object.entries(data.etf_details).forEach(([etfCode, details]) => {
          if (details.changes) {
            details.changes.forEach(change => {
              // We clone the item and add the source ETF to 'affected_etfs' so the UI doesn't crash
              // Note: This simple implementation lists duplicates separately.
              items.push({ ...change, affected_etfs: [etfCode] });
            });
          }
        });
      }
    } else {
      const etfData = data.etf_details[activeTab];
      if (etfData && etfData[type]) {
        items = [...etfData[type]];
      }
    }

    // Sort logic
    if (sortConfig.key) {
      items.sort((a, b) => {
        let aVal = a[sortConfig.key];
        let bVal = b[sortConfig.key];

        if (typeof aVal === 'string') {
          return sortConfig.direction === 'asc'
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal);
        }

        if (aVal < bVal) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aVal > bVal) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    return items;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl animate-pulse-subtle gradient-text font-bold">加載中... (請稍候，後端正在下載最新資料)</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-gray-400">
        <div className="text-xl mb-4 text-red-400 font-bold">無法連接伺服器</div>
        <p className="mb-4">請確認後端視窗 (黑色視窗) 是否正在執行...</p>
        <button
          onClick={fetchData}
          className="px-6 py-2 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 transition"
        >
          重試連線
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-8">
      <header className="mb-12 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-bold mb-2 gradient-text">ETF 持倉異動追蹤 (7PM更新)</h1>
          <p className="text-gray-400 flex items-center gap-2">
            <Calendar size={16} /> 比較日期: {data.dates?.new ? `${data.dates.new.slice(0, 4)}/${data.dates.new.slice(4, 6)}/${data.dates.new.slice(6, 8)}` : 'N/A'} vs {data.dates?.old ? `${data.dates.old.slice(0, 4)}/${data.dates.old.slice(4, 6)}/${data.dates.old.slice(6, 8)}` : 'N/A'}
          </p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab('aggregated')}
            className={`px-6 py-2 rounded-full transition-all ${activeTab === 'aggregated' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30' : 'bg-white/5 hover:bg-white/10'}`}
          >
            整合視角
          </button>
          {Object.keys(data.etf_details).map(etf => (
            <button
              key={etf}
              onClick={() => setActiveTab(etf)}
              className={`px-6 py-2 rounded-full transition-all ${activeTab === etf ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30' : 'bg-white/5 hover:bg-white/10'}`}
            >
              {etf}
            </button>
          ))}
        </div>
      </header>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
        <div className="glass-card">
          <div className="flex items-center gap-3 text-gray-400 mb-2 text-sm">
            <TrendingUp size={16} className="text-green-500" /> 總買入估計
          </div>
          <div className="text-2xl font-bold text-green-500">{data.summary.total_buy_str}</div>
        </div>
        <div className="glass-card">
          <div className="flex items-center gap-3 text-gray-400 mb-2 text-sm">
            <TrendingDown size={16} className="text-red-500" /> 總賣出估計
          </div>
          <div className="text-2xl font-bold text-red-500">{data.summary.total_sell_str}</div>
        </div>
        <div className="glass-card">
          <div className="flex items-center gap-3 text-gray-400 mb-2 text-sm">
            <Activity size={16} className="text-blue-500" /> 新增標的數
          </div>
          <div className="text-2xl font-bold">{data.summary.count_added}</div>
        </div>
        <div className="glass-card">
          <div className="flex items-center gap-3 text-gray-400 mb-2 text-sm">
            <Layers size={16} className="text-purple-500" /> 剔除標的數
          </div>
          <div className="text-2xl font-bold">{data.summary.count_removed}</div>
        </div>
      </div>

      <main>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <div className="glass-card">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <DollarSign size={20} className="text-indigo-400" />
                {activeTab === 'aggregated' ? '全 ETF 整合異動' : `${activeTab} 詳細異動`}
              </h2>

              <table>
                <thead>
                  <tr>
                    <th onClick={() => requestSort('ticker')} className="cursor-pointer hover:text-white transition-colors">
                      標的代號 {sortConfig.key === 'ticker' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </th>
                    <th onClick={() => requestSort('name')} className="cursor-pointer hover:text-white transition-colors">
                      名稱 {sortConfig.key === 'name' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </th>
                    <th onClick={() => requestSort('delta_shares')} className="text-right cursor-pointer hover:text-white transition-colors">
                      異動股數 {sortConfig.key === 'delta_shares' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </th>
                    {activeTab !== 'aggregated' && (
                      <th onClick={() => requestSort('new_shares')} className="text-right cursor-pointer hover:text-white transition-colors">
                        目前持倉 {sortConfig.key === 'new_shares' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </th>
                    )}
                    <th onClick={() => requestSort('monetary_value')} className="text-right cursor-pointer hover:text-white transition-colors">
                      估計金額 {sortConfig.key === 'monetary_value' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </th>
                    {activeTab === 'aggregated' && <th>涉及 ETF</th>}
                    <th className="text-center">狀態</th>
                  </tr>
                </thead>
                <tbody>
                  {getSortedData('changes').map((item, idx) => (
                    <tr key={idx} className="group hover:bg-white/[0.03] transition-colors">
                      <td className="font-mono text-indigo-300">{item.ticker}</td>
                      <td className="font-medium">{item.name}</td>
                      <td className={`text-right font-mono ${item.delta_shares > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {item.delta_shares > 0 ? '+' : ''}{formatNumber(item.delta_shares)}
                      </td>
                      {activeTab !== 'aggregated' && (
                        <td className="text-right text-gray-400 font-mono">
                          {formatNumber(item.new_shares)}
                        </td>
                      )}
                      <td className={`text-right font-bold font-mono ${item.monetary_value > 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {item.monetary_value > 0 ? '+' : ''}{item.monetary_value_str}
                      </td>
                      {activeTab === 'aggregated' && (
                        <td>
                          <div className="flex gap-1 flex-wrap">
                            {item.affected_etfs.map(etf => (
                              <span key={etf} className="text-[10px] bg-white/10 px-2 py-0.5 rounded border border-white/10">{etf}</span>
                            ))}
                          </div>
                        </td>
                      )}
                      <td className="text-center">
                        <span className={`status-badge ${item.delta_shares > 0 ? (item.old_shares === 0 ? 'badge-added' : 'badge-changed')
                          : (item.new_shares <= 1000 ? 'badge-removed' : 'badge-changed')
                          }`}>
                          {item.delta_shares > 0 ? (item.old_shares === 0 ? '新增' : '加碼')
                            : (item.new_shares <= 1000 ? '剔除' : '減持')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Secondary Table: Full Holdings (Only for individual ETFs) */}
            {activeTab !== 'aggregated' && (
              <div className="mt-12">
                <h2 className="text-2xl font-bold mb-4 gradient-text">{activeTab} 目前完整持倉</h2>
                <div className="glass-card rounded-2xl overflow-hidden">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/10 bg-white/[0.02]">
                        <th onClick={() => requestSort('ticker')} className="text-left p-4 cursor-pointer hover:text-white">代號</th>
                        <th onClick={() => requestSort('name')} className="text-left p-4 cursor-pointer hover:text-white">名稱</th>
                        <th onClick={() => requestSort('new_shares')} className="text-right p-4 cursor-pointer hover:text-white">持有股數</th>
                        <th onClick={() => requestSort('monetary_value')} className="text-right p-4 cursor-pointer hover:text-white">總市值</th>
                      </tr>
                    </thead>
                    <tbody>
                      {getSortedData('holdings').map((item, idx) => (
                        <tr key={idx} className="group hover:bg-white/[0.03] border-b border-white/5 last:border-0">
                          <td className="p-4 font-mono text-indigo-300">{item.ticker}</td>
                          <td className="p-4 font-medium">{item.name}</td>
                          <td className="p-4 text-right font-mono text-gray-300">{formatNumber(item.new_shares)}</td>
                          <td className="p-4 text-right font-mono font-bold text-blue-300">{item.monetary_value_str}</td>
                        </tr>
                      ))}
                      {getSortedData('holdings').length === 0 && (
                        <tr>
                          <td colSpan="4" className="p-8 text-center text-gray-500">
                            尚無持倉資料 (可能為全現金或讀取失敗)
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab !== 'aggregated' &&
              (!data.etf_details[activeTab].changes || data.etf_details[activeTab].changes.length === 0) && (
                <div className="py-20 text-center text-gray-500 italic">
                  此日期區間無異動資料
                </div>
              )}
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className="mt-20 text-center text-gray-600 text-sm">
        ETF Holding Tracker &copy; 2026 • 股票價格僅供參考
      </footer>
    </div >
  );
}

export default App;

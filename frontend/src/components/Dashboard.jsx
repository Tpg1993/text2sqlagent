import React, { useState, useEffect } from 'react';
import { BarChart3, Loader2, Trash2, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = ['#6366f1', '#22d3ee', '#fb923c', '#a3e635', '#f472b6'];

const SavedChartCard = ({ chart, onDelete }) => {
  const spec = chart.spec || {};
  const { type, data, xKey, yKey, title: specTitle } = spec;

  const renderChart = () => {
    if (!data || !xKey || !yKey) return <span className="text-slate-400 text-sm">No valid chart data</span>;
    switch (type) {
      case 'bar':
        return (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey={xKey} stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
            <Legend />
            <Bar dataKey={yKey} fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        );
      case 'line':
        return (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey={xKey} stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
            <Legend />
            <Line type="monotone" dataKey={yKey} stroke="#22d3ee" strokeWidth={2} dot={false} />
          </LineChart>
        );
      case 'pie':
        return (
          <PieChart>
            <Pie data={data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" outerRadius={80} label>
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
            <Legend />
          </PieChart>
        );
      default:
        return <span className="text-slate-400 text-sm">Unsupported chart type: {type}</span>;
    }
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 shadow-lg hover:shadow-indigo-500/10 hover:border-indigo-500/40 transition-all">
      <div className="flex justify-between items-center mb-3">
        <div>
          <h3 className="font-semibold text-slate-100 text-sm">{chart.title}</h3>
          <p className="text-xs text-slate-500 mt-0.5">By {chart.creator}</p>
        </div>
        {onDelete && (
          <button onClick={() => onDelete(chart.id)} className="text-slate-500 hover:text-red-400 transition" title="Delete">
            <Trash2 size={15} />
          </button>
        )}
      </div>
      <ResponsiveContainer width="100%" height={200}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
};

const Dashboard = () => {
  const { user, logout } = useAuth();
  const [charts, setCharts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCharts = async () => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/charts/', {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });
      if (!response.ok) throw new Error(`Failed to load charts: ${response.status}`);
      setCharts(await response.json());
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteChart = async (id) => {
    if (!window.confirm('Remove this chart from the dashboard?')) return;
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`/api/v1/charts/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });
      if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
      setCharts(prev => prev.filter(c => c.id !== id));
    } catch (err) {
      console.error(err);
      alert('Failed to delete chart: ' + err.message);
    }
  };

  useEffect(() => { fetchCharts(); }, []);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between border-b border-slate-700 pb-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2 text-white">
              <BarChart3 className="text-indigo-400" /> Dashboard
            </h1>
            <p className="text-slate-400 text-sm mt-1">Your pinned charts and visualizations</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={fetchCharts} className="text-sm text-indigo-400 hover:text-indigo-300 transition font-medium">
              ↻ Refresh
            </button>
            {user && (
              <div className="flex items-center gap-2 bg-slate-700 rounded-full px-3 py-1.5">
                <div className="w-6 h-6 rounded-full bg-indigo-500 flex items-center justify-center text-xs font-bold text-white">
                  {(user.username || 'U')[0].toUpperCase()}
                </div>
                <span className="text-sm text-slate-200 font-medium">{user.username}</span>
                <button onClick={logout} title="Logout" className="text-slate-400 hover:text-red-400 transition ml-1">
                  <LogOut size={14} />
                </button>
              </div>
            )}
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-400">
            <Loader2 className="animate-spin text-indigo-400" size={36} />
            <p>Loading charts...</p>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-900/30 border border-red-700 text-red-300 rounded-lg text-sm">{error}</div>
        ) : charts.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-slate-700 rounded-xl">
            <BarChart3 size={48} className="mx-auto text-slate-600 mb-4" />
            <h3 className="text-lg font-medium text-slate-400">No charts saved yet</h3>
            <p className="text-slate-500 text-sm mt-1">Generate a chart in the chat and click <strong>"Pin to Dashboard"</strong></p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {charts.map(chart => (
              <SavedChartCard key={chart.id} chart={chart} onDelete={deleteChart} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;

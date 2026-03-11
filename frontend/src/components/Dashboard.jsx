import React, { useState, useEffect } from 'react';
import { BarChart3, Trash2, ExternalLink, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
// Lazy load Vega to keep bundle size manageable if it's heavy
import vegaEmbed from 'vega-embed';

const SavedChartCard = ({ chart, onDelete }) => {
  const containerRef = React.useRef(null);

  useEffect(() => {
    if (chart.spec && containerRef.current) {
      vegaEmbed(containerRef.current, chart.spec, { actions: false }).catch(console.error);
    }
  }, [chart.spec]);

  return (
    <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-semibold text-gray-800">{chart.title}</h3>
          <p className="text-xs text-gray-500">Saved by {chart.creator} on {new Date(chart.created_at).toLocaleDateString()}</p>
        </div>
        
        <div className="flex gap-2 text-gray-400">
          <button onClick={() => window.open(URL.createObjectURL(new Blob([JSON.stringify(chart.spec, null, 2)], {type: 'application/json'})), '_blank')} className="hover:text-blue-500 transition" title="View Spec">
            <ExternalLink size={16} />
          </button>
          {/* Note: Delete API not yet implemented but UI is ready */}
        </div>
      </div>
      
      <div 
        ref={containerRef} 
        className="w-full h-48 flex items-center justify-center overflow-hidden"
      >
        {/* Vega Chart mounts here */}
        {!chart.spec && <span className="text-gray-400 text-sm">No valid spec</span>}
      </div>
    </div>
  );
};

const Dashboard = () => {
  const { user } = useAuth();
  const [charts, setCharts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCharts = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/charts', {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });
      if (!response.ok) throw new Error('Failed to load charts');
      const data = await response.json();
      setCharts(data);
    } catch (err) {
      console.error(err);
      setError("Failed to load saved charts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCharts();
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart3 className="text-indigo-600" /> Executive Dashboard
          </h1>
          <p className="text-gray-600 mt-1">Saved intelligence workflows and visualizations.</p>
        </div>
        <button onClick={fetchCharts} className="text-sm font-medium text-blue-600 hover:text-blue-800 transition">
          Refresh Data
        </button>
      </div>

      {error ? (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg">{error}</div>
      ) : loading ? (
        <div className="flex justify-center flex-col items-center py-12 text-gray-500 gap-4">
          <Loader2 className="animate-spin text-blue-500" size={32} />
          <p>Loading your insights...</p>
        </div>
      ) : charts.length === 0 ? (
        <div className="text-center py-16 bg-gray-50 rounded-xl border border-gray-100 border-dashed">
          <BarChart3 size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-700">No charts saved yet</h3>
          <p className="text-gray-500 mt-1 max-w-sm mx-auto">
            When you generate a useful chart in the chat interface, click "Save to Dashboard" to pin it here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {charts.map(chart => (
            <SavedChartCard key={chart.id} chart={chart} />
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;

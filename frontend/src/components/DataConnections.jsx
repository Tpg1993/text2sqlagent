import React, { useState, useEffect } from 'react';
import { Database, Upload, Save, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const DataConnections = () => {
  const { user } = useAuth();
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '', db_type: 'postgres', host: '', port: '', username: '', password: '', database: ''
  });

  const fetchConnections = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/connections', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      if (!response.ok) throw new Error('Failed to load connections');
      const data = await response.json();
      setConnections(data);
    } catch (err) {
      console.error(err);
      setError('Failed to load connections');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConnections();
  }, []);

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSaveConnection = async (e) => {
    e.preventDefault();
    if (user?.role !== 'admin') {
      setError("Only admins can save connections.");
      return;
    }
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/connections', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        let errorData;
        try { errorData = await response.json(); } catch(e) {}
        throw new Error(errorData?.detail || "Failed to save connection");
      }
      
      setSuccessMsg("Connection saved successfully!");
      setFormData({name: '', db_type: 'postgres', host: '', port: '', username: '', password: '', database: ''});
      fetchConnections();
    } catch (err) {
      setError(err.message || "Failed to save connection");
    } finally {
      setLoading(false);
      setTimeout(() => setSuccessMsg(null), 3000);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (user?.role !== 'admin') {
      setError("Only admins can upload CSVs.");
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploading(true);
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/connections/csv', {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: formData
      });
      
      if (!response.ok) {
        let errorData;
        try { errorData = await response.json(); } catch(e) {}
        throw new Error(errorData?.detail || "Upload failed");
      }
      const data = await response.json();
      setSuccessMsg(data.message);
      // Wait a bit to let Backend ingest, though it's synchronous here
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = null; // reset
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Database className="text-blue-600" /> Data Connections
        </h1>
        <p className="text-gray-600 mt-1">Manage database credentials and upload ad-hoc datasets.</p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
          <AlertCircle size={20} /> {error}
        </div>
      )}
      
      {successMsg && (
        <div className="p-4 bg-green-50 text-green-700 rounded-lg flex items-center gap-2">
          <CheckCircle size={20} /> {successMsg}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-8">
        
        {/* Connection Form */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-semibold mb-4 text-gray-800 border-b pb-2">Add Database Connection</h2>
          <form onSubmit={handleSaveConnection} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                <input type="text" name="name" required value={formData.name} onChange={handleInputChange} className="w-full p-2 border rounded-md" placeholder="e.g. Prod DB" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                <select name="db_type" value={formData.db_type} onChange={handleInputChange} className="w-full p-2 border rounded-md bg-white">
                  <option value="postgres">PostgreSQL</option>
                  <option value="snowflake">Snowflake</option>
                  <option value="bigquery">BigQuery</option>
                  <option value="sqlite">SQLite</option>
                </select>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Host</label>
                <input type="text" name="host" value={formData.host} onChange={handleInputChange} className="w-full p-2 border rounded-md" placeholder="localhost" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                <input type="number" name="port" value={formData.port} onChange={handleInputChange} className="w-full p-2 border rounded-md" placeholder="5432" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input type="text" name="username" value={formData.username} onChange={handleInputChange} className="w-full p-2 border rounded-md" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input type="password" name="password" value={formData.password} onChange={handleInputChange} className="w-full p-2 border rounded-md" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Database Name</label>
              <input type="text" name="database" value={formData.database} onChange={handleInputChange} className="w-full p-2 border rounded-md" />
            </div>

            <button type="submit" disabled={loading || user?.role !== 'admin'} className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition disabled:opacity-50">
              <Save size={18} /> Save Connection
            </button>
          </form>
        </div>

        {/* Action Column */}
        <div className="space-y-8">
          
          {/* CSV Upload */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
             <h2 className="text-lg font-semibold mb-4 text-gray-800 border-b pb-2">Turnkey CSV Upload</h2>
             <p className="text-sm text-gray-600 mb-4">
               Upload a CSV to instantly query it with natural language. We'll automatically infer the schema and create a table.
             </p>
             <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center bg-gray-50 hover:bg-gray-100 transition">
               <input 
                 type="file" 
                 id="csv-upload" 
                 accept=".csv" 
                 className="hidden" 
                 onChange={handleFileUpload}
                 disabled={uploading || user?.role !== 'admin'}
               />
               <label htmlFor="csv-upload" className={`cursor-pointer flex flex-col items-center justify-center gap-2 ${(uploading || user?.role !== 'admin') ? 'opacity-50 cursor-not-allowed' : ''}`}>
                 {uploading ? <Loader2 className="animate-spin text-blue-500" size={32} /> : <Upload className="text-blue-500" size={32} />}
                 <span className="font-medium text-gray-700">
                   {uploading ? 'Processing CSV...' : 'Click to upload CSV'}
                 </span>
                 <span className="text-xs text-gray-500">Admin only</span>
               </label>
             </div>
          </div>

          {/* Saved Connections List */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h2 className="text-lg font-semibold mb-4 text-gray-800 border-b pb-2">Active Connections</h2>
            {loading && !connections.length ? (
              <div className="flex justify-center p-4"><Loader2 className="animate-spin text-blue-500" /></div>
            ) : connections.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No connections saved yet.</p>
            ) : (
              <div className="space-y-3">
                {connections.map(c => (
                  <div key={c.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                    <div>
                      <h3 className="font-medium text-gray-800">{c.name}</h3>
                      <p className="text-xs text-gray-500">{c.db_type} • {c.host || 'local'}</p>
                    </div>
                    <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full font-medium">Connected</span>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};

export default DataConnections;

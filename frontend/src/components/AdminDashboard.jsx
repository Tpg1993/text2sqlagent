import React, { useState, useEffect } from 'react';
import { ShieldCheck, Users, Search, AlertOctagon, Activity, FileLock2, Clock } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const AdminDashboard = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (user && user.role !== 'admin') {
            navigate('/');
            return;
        }

        const fetchAnalytics = async () => {
            try {
                setLoading(true);
                const token = localStorage.getItem('token');
                const response = await fetch('/api/v1/admin/analytics', {
                    headers: { 'Authorization': token ? `Bearer ${token}` : '' }
                });
                if (!response.ok) throw new Error('Failed to fetch analytics');
                const data = await response.json();
                setAnalytics(data);
            } catch (err) {
                console.error(err);
                setError("Failed to fetch admin analytics.");
            } finally {
                setLoading(false);
            }
        };

        fetchAnalytics();
    }, [user, navigate]);

    if (loading) {
        return <div className="p-8 text-center text-gray-500">Loading governance data...</div>;
    }

    if (error) {
        return <div className="p-8 text-center text-red-500">{error}</div>;
    }

    const { metrics, intents, recent_logs } = analytics;

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8 pb-12">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <ShieldCheck className="text-emerald-600" /> Admin Governance
                </h1>
                <p className="text-gray-600 mt-1">Monitor AI usage, security blocks, and data privacy actions.</p>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center gap-4">
                    <div className="p-4 bg-blue-50 text-blue-600 rounded-lg">
                        <Activity size={24} />
                    </div>
                    <div>
                        <p className="text-2xl font-bold text-gray-800">{metrics.total_queries}</p>
                        <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Total Queries</p>
                    </div>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center gap-4">
                    <div className="p-4 bg-red-50 text-red-600 rounded-lg">
                        <AlertOctagon size={24} />
                    </div>
                    <div>
                        <p className="text-2xl font-bold text-gray-800">{metrics.blocked_count}</p>
                        <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">NeMo Blocks</p>
                    </div>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center gap-4">
                    <div className="p-4 bg-purple-50 text-purple-600 rounded-lg">
                        <FileLock2 size={24} />
                    </div>
                    <div>
                        <p className="text-2xl font-bold text-gray-800">{metrics.pii_count}</p>
                        <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">PII Scrubbed</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Intent Distribution */}
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                    <h2 className="text-lg font-semibold mb-4 text-gray-800 border-b pb-2">Query Intents</h2>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={intents}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {intents.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Audit Log Table */}
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm lg:col-span-2 overflow-hidden flex flex-col">
                    <h2 className="text-lg font-semibold mb-4 text-gray-800 border-b pb-2 flex items-center justify-between">
                        <span>Recent Audit Logs</span>
                        <span className="text-xs font-normal text-gray-400">Last 20 events</span>
                    </h2>
                    
                    <div className="overflow-auto flex-1 h-64">
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs uppercase bg-gray-50 text-gray-600 sticky top-0">
                                <tr>
                                    <th className="px-4 py-3">Time</th>
                                    <th className="px-4 py-3">User</th>
                                    <th className="px-4 py-3">Query</th>
                                    <th className="px-4 py-3">Intent</th>
                                    <th className="px-4 py-3">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {recent_logs.map(log => (
                                    <tr key={log.id} className="hover:bg-gray-50">
                                        <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                                            <div className="flex items-center gap-1">
                                                <Clock size={12} />
                                                {new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 font-medium text-gray-700">{log.username}</td>
                                        <td className="px-4 py-3 text-gray-800 truncate max-w-[200px]" title={log.query}>
                                            {log.query}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600">{log.intent}</span>
                                        </td>
                                        <td className="px-4 py-3 flex gap-1">
                                            {log.blocked ? (
                                                <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">Blocked</span>
                                            ) : (
                                                <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">Clear</span>
                                            )}
                                            {log.pii_scrubbed && (
                                                <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium" title="PII tokens generated or restored">PII</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                                {recent_logs.length === 0 && (
                                    <tr>
                                        <td colSpan="5" className="px-4 py-8 text-center text-gray-500 italic">No logs found.</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AdminDashboard;

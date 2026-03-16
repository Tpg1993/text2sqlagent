import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';
import { Save, Check } from 'lucide-react';
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function ChartRenderer({ spec }) {
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    if (!spec || !spec.type || !spec.data) return null;

    const { type, data, xKey, yKey, title } = spec;

    const handleSave = async () => {
        try {
            setSaving(true);
            const token = localStorage.getItem('token');
            const res = await fetch('/api/v1/charts/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': token ? `Bearer ${token}` : ''
                },
                body: JSON.stringify({
                    title: title || 'Untitled Chart',
                    spec: spec 
                })
            });
            
            if (!res.ok) {
                const errBody = await res.text();
                console.error('Save chart error:', res.status, errBody);
                throw new Error(`Failed to save chart (${res.status}): ${errBody}`);
            }
            
            setSaved(true);
            setTimeout(() => setSaved(false), 3000);
        } catch (error) {
            console.error("Failed to save chart", error);
            alert("Failed to save chart.");
        } finally {
            setSaving(false);
        }
    };

    const renderChart = () => {
        switch (type) {
            case 'bar':
                return (
                    <BarChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                        <XAxis dataKey={xKey} stroke="#ccc" />
                        <YAxis stroke="#ccc" />
                        <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none' }} />
                        <Legend />
                        <Bar dataKey={yKey} fill="#8884d8" />
                    </BarChart>
                );
            case 'line':
                return (
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                        <XAxis dataKey={xKey} stroke="#ccc" />
                        <YAxis stroke="#ccc" />
                        <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none' }} />
                        <Legend />
                        <Line type="monotone" dataKey={yKey} stroke="#82ca9d" />
                    </LineChart>
                );
            case 'pie':
                return (
                    <PieChart>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey={yKey} // Recharts often needs a value key
                            nameKey={xKey}
                        >
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none' }} />
                    </PieChart>
                )
            default:
                return <div>Unsupported chart type: {type}</div>
        }
    };

    return (
        <div className="w-full h-64 p-4 bg-slate-800 rounded-lg shadow-lg my-4 relative group">
            <div className="flex justify-between items-center mb-2">
                {title ? <h3 className="font-semibold text-slate-300">{title}</h3> : <div></div>}
                <button 
                  onClick={handleSave} 
                  disabled={saving || saved}
                  className="flex items-center gap-1 text-xs bg-slate-700 hover:bg-indigo-600 text-slate-200 py-1 px-2 rounded border border-slate-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {saved ? <Check size={14} className="text-green-400" /> : <Save size={14} />}
                    {saved ? 'Saved!' : 'Pin to Dashboard'}
                </button>
            </div>
            <ResponsiveContainer width="100%" height="90%">
                {renderChart()}
            </ResponsiveContainer>
        </div>
    );
}

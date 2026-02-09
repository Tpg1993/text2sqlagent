import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function ChartRenderer({ spec }) {
    if (!spec || !spec.type || !spec.data) return null;

    const { type, data, xKey, yKey, title } = spec;

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
        <div className="w-full h-64 p-4 bg-slate-800 rounded-lg shadow-lg my-4">
            {title && <h3 className="text-center mb-2 font-semibold text-slate-300">{title}</h3>}
            <ResponsiveContainer width="100%" height="100%">
                {renderChart()}
            </ResponsiveContainer>
        </div>
    );
}

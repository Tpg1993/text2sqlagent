import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Database, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import ChartRenderer from './components/ChartRenderer';
import { chat } from './api/client';

function App() {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Hello! I am Agenthic, data assistant. Ask me about sales data (SQL) or support policies (RAG).' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [agentProgress, setAgentProgress] = useState('');
    const scrollRef = useRef(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);
        setAgentProgress('🤖 Starting...');

        try {
            const res = await chat(userMsg.content, (progressMsg) => {
                setAgentProgress(progressMsg);
            });
            const assistantMsg = {
                role: 'assistant',
                content: res.response,
                chart: res.chart,
                data: res.data
            };
            setMessages(prev => [...prev, assistantMsg]);
        } catch (err) {
            let errorMsg = "Sorry, something went wrong: " + err.message;

            // Check for rate limit error with retry time
            if (err.data && err.data.retry_after) {
                // Determine if retry_after is just seconds or full message
                const seconds = err.data.retry_after.replace('s', '');
                errorMsg = `⏳ **Rate Limit Hit**: Please wait **${seconds} seconds** before sending another message.`;
            }

            setMessages(prev => [...prev, { role: 'assistant', content: errorMsg }]);
        } finally {
            setLoading(false);
            setAgentProgress('');
        }
    };

    return (
        <div className="flex flex-col h-screen bg-slate-950 text-slate-200">
            {/* Header */}
            <header className="flex items-center p-4 border-b border-slate-800 bg-slate-900 shadow-md">
                <div className="p-2 bg-indigo-600 rounded-lg mr-3">
                    <Bot className="w-6 h-6 text-white" />
                </div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                    Agenthic Data Assistant
                </h1>
            </header>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`flex max-w-3xl ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} gap-3`}>

                            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-indigo-600' : 'bg-slate-700'}`}>
                                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                            </div>

                            <div className={`flex flex-col gap-2 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                <div className={`p-4 rounded-2xl shadow-sm ${msg.role === 'user'
                                    ? 'bg-indigo-600 text-white rounded-tr-sm'
                                    : 'bg-slate-800 border border-slate-700 rounded-tl-sm'
                                    }`}>
                                    <ReactMarkdown className="prose prose-invert max-w-none text-sm leading-relaxed">
                                        {msg.content}
                                    </ReactMarkdown>
                                </div>

                                {/* Optional Data Table */}
                                {msg.data && (
                                    <div className="bg-slate-900 rounded-lg p-2 border border-slate-700 w-full overflow-x-auto">
                                        <table className="w-full text-xs text-left text-slate-400">
                                            <thead className="text-xs uppercase bg-slate-800 text-slate-300">
                                                <tr>
                                                    {Object.keys(msg.data[0] || {}).map(key => (
                                                        <th key={key} className="px-3 py-2">{key}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {msg.data.slice(0, 5).map((row, i) => ( // Limit rows for view
                                                    <tr key={i} className="border-b border-slate-800 hover:bg-slate-800">
                                                        {Object.values(row).map((val, j) => (
                                                            <td key={j} className="px-3 py-2">{val}</td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                        {msg.data.length > 5 && <p className="text-xs text-center p-1 text-slate-500">Showing top 5 of {msg.data.length} rows</p>}
                                    </div>
                                )}

                                {/* Chart */}
                                {msg.chart && (
                                    <ChartRenderer spec={msg.chart} />
                                )}
                            </div>
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="flex items-center gap-2 bg-slate-800 px-4 py-2 rounded-2xl rounded-tl-sm border border-slate-700 ml-11">
                            <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                            <span className="text-xs text-slate-400">{agentProgress || 'Thinking...'}</span>
                        </div>
                    </div>
                )}
                <div ref={scrollRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/50 backdrop-blur-sm">
                <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about sales trends or return policies..."
                        className="w-full bg-slate-800 text-slate-100 border border-slate-700 rounded-xl pl-4 pr-12 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all shadow-inner placeholder:text-slate-500"
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="absolute right-2 top-2 p-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Send size={18} />
                    </button>
                </form>
                <div className="text-center mt-2 text-xs text-slate-600 flex justify-center gap-4">
                    <span className="flex items-center gap-1"><Database size={10} /> SQLite Memory</span>
                    <span className="flex items-center gap-1"><FileText size={10} /> RAG Enabled</span>
                </div>
            </div>
        </div>
    );
}

export default App;

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Database, FileText, LogOut, Clock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import DOMPurify from 'dompurify';
import ChartRenderer from './ChartRenderer';
import { chat, pollApprovalStatus } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function ChatInterface() {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Hello! I am Agenthic, your data assistant. Ask me about sales data (SQL) or support policies (RAG).' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [agentProgress, setAgentProgress] = useState('');
    // Track active approval polls so we can cancel them on unmount
    const activePollsRef = useRef({});
    const scrollRef = useRef(null);
    const { logout, user } = useAuth();
    const navigate = useNavigate();

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            Object.values(activePollsRef.current).forEach(cancelFn => cancelFn());
        };
    }, []);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    /**
     * Start a polling loop for a pending approval request.
     * Resolves into the chat message list once the admin approves or rejects.
     * Polls every 3 seconds for up to 10 minutes.
     */
    const startApprovalPolling = (requestId, pendingMsgIndex) => {
        const MAX_POLLS = 100; // 100 × 3s = 5 minutes, matches backend auto-reject timeout
        let pollCount = 0;
        let cancelled = false;

        const cancel = () => { cancelled = true; };
        activePollsRef.current[requestId] = cancel;

        const poll = async () => {
            if (cancelled || pollCount >= MAX_POLLS) {
                // Replace pending message with timeout message
                setMessages(prev => {
                    const updated = [...prev];
                    updated[pendingMsgIndex] = {
                        ...updated[pendingMsgIndex],
                        content: updated[pendingMsgIndex].content + '\n\n> ⏱️ Approval request timed out after 10 minutes.',
                        isPending: false,
                    };
                    return updated;
                });
                delete activePollsRef.current[requestId];
                return;
            }

            pollCount++;
            try {
                const statusRes = await pollApprovalStatus(requestId);

                if (statusRes.status === 'approved') {
                    // Replace the pending message with approved result
                    setMessages(prev => {
                        const updated = [...prev];
                        updated[pendingMsgIndex] = {
                            role: 'assistant',
                            content: `✅ **Query Approved!** Results are ready:`,
                            data: statusRes.results || [],
                            isPending: false,
                        };
                        return updated;
                    });
                    delete activePollsRef.current[requestId];
                    return;
                }

                if (statusRes.status === 'rejected') {
                    setMessages(prev => {
                        const updated = [...prev];
                        updated[pendingMsgIndex] = {
                            role: 'assistant',
                            content: `❌ **Query Rejected.** Reason: ${statusRes.message || 'No reason provided.'}`,
                            isPending: false,
                        };
                        return updated;
                    });
                    delete activePollsRef.current[requestId];
                    return;
                }

                // Still pending — schedule next poll
                setTimeout(poll, 3000);
            } catch (err) {
                if (err.status === 401) {
                    logout();
                    navigate('/login');
                    return;
                }
                // Non-fatal: retry after a pause
                setTimeout(poll, 5000);
            }
        };

        // Start first poll after 3 seconds
        setTimeout(poll, 3000);
        return cancel;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);
        setAgentProgress('Starting...');

        try {
            const res = await chat(userMsg.content, (data) => {
                if (typeof data === 'string') {
                    setAgentProgress(data);
                } else if (data && data.response) {
                    // SSE approval result (best-effort)
                    const assistantMsg = {
                        role: 'assistant',
                        content: data.response,
                        data: data.data
                    };
                    setMessages(prev => [...prev, assistantMsg]);
                }
            });

            if (res.approval_status === 'pending' && res.response) {
                // Extract the request ID from the response message
                const match = res.response.match(/Approval request ID: ([a-f0-9-]+)/i);
                const requestId = match ? match[1] : null;

                // Add a pending message that will be updated when approved/rejected
                setMessages(prev => {
                    const pendingMsg = {
                        role: 'assistant',
                        content: res.response + (requestId
                            ? `\n\n> ⏳ Waiting for admin approval... The result will appear here automatically.`
                            : ''),
                        isPending: !!requestId,
                    };
                    const updated = [...prev, pendingMsg];

                    // Start polling now that we know the index
                    if (requestId) {
                        const pendingMsgIndex = updated.length - 1;
                        startApprovalPolling(requestId, pendingMsgIndex);
                    }

                    return updated;
                });
            } else {
                const assistantMsg = {
                    role: 'assistant',
                    content: res.response,
                    chart: res.chart,
                    data: res.data
                };
                setMessages(prev => [...prev, assistantMsg]);
            }
        } catch (err) {
            if (err.status === 401) {
                logout();
                navigate('/login');
                return;
            }
            let errorMsg = "Sorry, something went wrong: " + err.message;

            if (err.data && err.data.retry_after !== undefined && err.data.retry_after !== null) {
                const seconds = String(err.data.retry_after).replace('s', '');
                errorMsg = `Rate limit hit: please wait ${seconds} seconds before sending another message.`;
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
            <header className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900 shadow-md">
                <div className="flex items-center">
                    <div className="p-2 bg-indigo-600 rounded-lg mr-3">
                        <Bot className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                            Agenthic Data Assistant
                        </h1>
                        <p className="text-xs text-slate-500">Logged in as {user?.username}</p>
                    </div>
                </div>
                <button
                    onClick={handleLogout}
                    className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                    title="Logout"
                >
                    <LogOut className="w-5 h-5" />
                </button>
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
                                    : msg.isPending
                                        ? 'bg-amber-950/60 border border-amber-700/50 rounded-tl-sm'
                                        : 'bg-slate-800 border border-slate-700 rounded-tl-sm'
                                    }`}>
                                    {msg.isPending && (
                                        <div className="flex items-center gap-2 mb-2 text-amber-400 text-xs">
                                            <Clock size={12} className="animate-pulse" />
                                            <span>Waiting for admin approval…</span>
                                        </div>
                                    )}
                                    <ReactMarkdown className="prose prose-invert max-w-none text-sm leading-relaxed">
                                        {DOMPurify.sanitize(msg.content)}
                                    </ReactMarkdown>
                                </div>

                                {/* Optional Data Table */}
                                {msg.data && msg.data.length > 0 && (
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
                                                {msg.data.slice(0, 50).map((row, i) => (
                                                    <tr key={i} className="border-b border-slate-800 hover:bg-slate-800">
                                                        {Object.values(row).map((val, j) => (
                                                            <td key={j} className="px-3 py-2">{String(val)}</td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                        {msg.data.length > 50 && <p className="text-xs text-center p-1 text-slate-500">Showing top 50 of {msg.data.length} rows</p>}
                                    </div>
                                )}
                                {msg.data && msg.data.length === 0 && (
                                    <div className="bg-slate-800 rounded-lg p-3 border border-slate-700 text-xs text-slate-400 italic">
                                        Query returned no results.
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

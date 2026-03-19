import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Database, FileText, LogOut, Clock, BarChart3, ShieldCheck, ChevronDown, ChevronUp, Info, Menu, X, MessageSquare, ThumbsUp, ThumbsDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import DOMPurify from 'dompurify';
import ChartRenderer from './ChartRenderer';
import { chat, pollApprovalStatus, executeCorrectedSql, getSessions, getSessionHistory, submitFeedback } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

function PaginatedTable({ data }) {
    const [page, setPage] = useState(0);
    const rowsPerPage = 50;
    const totalPages = Math.ceil(data.length / rowsPerPage);
    const currentData = data.slice(page * rowsPerPage, (page + 1) * rowsPerPage);

    return (
        <div className="bg-slate-900 rounded-lg p-2 border border-slate-700 w-full overflow-hidden flex flex-col mt-2">
            <div className="overflow-x-auto">
                <table className="w-full text-xs text-left text-slate-400 min-w-max">
                    <thead className="text-xs uppercase bg-slate-800 text-slate-300">
                        <tr>
                            {Object.keys(data[0] || {}).map(key => (
                                <th key={key} className="px-3 py-2">{key}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {currentData.map((row, i) => (
                            <tr key={i} className="border-b border-slate-800 hover:bg-slate-800">
                                {Object.values(row).map((val, j) => (
                                    <td key={j} className="px-3 py-2">{String(val)}</td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {totalPages > 1 && (
                <div className="flex items-center justify-between p-2 pb-0 mt-2 border-t border-slate-800">
                    <span className="text-xs text-slate-500">Showing {page * rowsPerPage + 1} to {Math.min((page + 1) * rowsPerPage, data.length)} of {data.length} rows</span>
                    <div className="flex gap-2">
                        <button disabled={page === 0} onClick={() => setPage(page - 1)} className="px-2 py-1 bg-slate-800 text-slate-300 rounded disabled:opacity-50 text-xs hover:bg-slate-700 transition-colors">Prev</button>
                        <button disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)} className="px-2 py-1 bg-slate-800 text-slate-300 rounded disabled:opacity-50 text-xs hover:bg-slate-700 transition-colors">Next</button>
                    </div>
                </div>
            )}
            {totalPages <= 1 && data.length > 50 && (
                <p className="text-xs text-center p-1 text-slate-500 mt-2">Showing all {data.length} rows</p>
            )}
        </div>
    );
}

export default function ChatInterface() {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Hello! I am Agenthic, your data assistant. Ask me about sales data (SQL) or support policies (RAG).' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [agentProgress, setAgentProgress] = useState('');
    
    // Sidebar & History State
    const [sessions, setSessions] = useState([]);
    const [currentSessionId, setCurrentSessionId] = useState(null);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    
    // For SQL Self-Correction
    const [editingSqlIndexes, setEditingSqlIndexes] = useState({});
    
    // For Metadata Dropdown
    const [expandedMetaIndexes, setExpandedMetaIndexes] = useState({});
    
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
        loadSessions();
    }, []);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, agentProgress]);

    const loadSessions = async () => {
        try {
            const data = await getSessions();
            setSessions(data);
        } catch (e) {
            console.error("Failed to load sessions", e);
        }
    };

    const handleSelectSession = async (sessionId) => {
        setCurrentSessionId(sessionId);
        setLoading(true);
        try {
            const history = await getSessionHistory(sessionId);
            if (history.length > 0) {
                setMessages(history);
            } else {
                setMessages([{ role: 'assistant', content: 'Session empty.' }]);
            }
        } catch (e) {
            console.error(e);
            setMessages([{ role: 'assistant', content: 'Failed to load session history.' }]);
        } finally {
            setLoading(false);
        }
    };

    const handleNewChat = () => {
        setCurrentSessionId(null);
        setMessages([
            { role: 'assistant', content: 'Hello! I am Agenthic, your data assistant. Ask me about sales data (SQL) or support policies (RAG).' }
        ]);
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const toggleMetadata = (index) => {
        setExpandedMetaIndexes(prev => ({ ...prev, [index]: !prev[index] }));
    };

    const handleFeedback = async (messageIndex, messageId, val) => {
        // Optimistic UI update
        const prevMessages = [...messages];
        const prevVal = prevMessages[messageIndex].feedback;
        prevMessages[messageIndex].feedback = prevVal === val ? null : val;
        setMessages(prevMessages);

        if (messageId) {
            try {
                await submitFeedback(messageId, prevVal === val ? null : val);
            } catch (e) {
                console.error("Failed to submit feedback", e);
                // Revert on error
                const reverted = [...messages];
                reverted[messageIndex].feedback = prevVal;
                setMessages(reverted);
            }
        }
    };

    const startApprovalPolling = (requestId, pendingMsgIndex) => {
        const MAX_POLLS = 100;
        let pollCount = 0;
        let cancelled = false;

        const cancel = () => { cancelled = true; };
        activePollsRef.current[requestId] = cancel;

        const poll = async () => {
            if (cancelled || pollCount >= MAX_POLLS) {
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

                setTimeout(poll, 3000);
            } catch (err) {
                if (err.status === 401) {
                    logout();
                    navigate('/login');
                    return;
                }
                setTimeout(poll, 5000);
            }
        };

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
                    const assistantMsg = {
                        role: 'assistant',
                        content: data.response,
                        data: data.data
                    };
                    setMessages(prev => [...prev, assistantMsg]);
                }
            }, currentSessionId);

            // Fetch sessions again to update sidebar title if it's a new session
            loadSessions();

            if (res.approval_status === 'pending' && res.response) {
                const match = res.response.match(/Approval request ID: ([a-f0-9-]+)/i);
                const requestId = match ? match[1] : null;

                setMessages(prev => {
                    const pendingMsg = {
                        role: 'assistant',
                        content: res.response + (requestId
                            ? `\n\n> ⏳ Waiting for admin approval... The result will appear here automatically.`
                            : ''),
                        isPending: !!requestId,
                    };
                    const updated = [...prev, pendingMsg];

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
                    data: res.data,
                    failed_sql: res.failed_sql,
                    schema_context: res.schema_context,
                    llm_used: res.llm_used,
                    sql_query: res.sql_query,
                    retrieved_docs: res.retrieved_docs,
                    reasoning: res.reasoning
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

    const handleSqlCorrectionEdit = (index, newSql) => {
        setEditingSqlIndexes(prev => ({
            ...prev,
            [index]: newSql
        }));
    };

    const handleSqlCorrectionSubmit = async (index, msg) => {
        const sqlToExecute = editingSqlIndexes[index] !== undefined ? editingSqlIndexes[index] : msg.failed_sql;
        if (!sqlToExecute?.trim()) return;

        setLoading(true);
        setAgentProgress('Executing corrected SQL...');

        try {
            const res = await executeCorrectedSql(sqlToExecute);
            
            const assistantMsg = {
                role: 'assistant',
                content: res.response || "Corrected SQL executed.",
                data: res.data,
                chart: res.chart
            };
            setMessages(prev => [...prev, assistantMsg]);
            
            setEditingSqlIndexes(prev => {
                const next = {...prev};
                delete next[index];
                return next;
            });
        } catch (err) {
            let errorMsg = "Correction failed: " + err.message;
            setMessages(prev => [...prev, { role: 'assistant', content: errorMsg }]);
        } finally {
            setLoading(false);
            setAgentProgress('');
        }
    };

    return (
        <div className="flex h-screen bg-slate-950 text-slate-200 overflow-hidden">
            
            {/* Sidebar */}
            {sidebarOpen && (
                <div className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col transition-all shrink-0 z-10">
                    <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                        <span className="font-semibold text-sm tracking-widest text-slate-400">CHATS</span>
                        <button onClick={() => setSidebarOpen(false)} className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition-colors">
                            <X size={16} />
                        </button>
                    </div>
                    <div className="p-4">
                        <button 
                            onClick={handleNewChat}
                            className="w-full bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-lg py-2 px-3 text-sm font-medium transition-colors flex items-center justify-center gap-2"
                        >
                            <MessageSquare size={16} /> New Chat
                        </button>
                    </div>
                    <div className="flex-1 overflow-y-auto px-2 space-y-1 pb-4">
                        {sessions.map(s => (
                            <button 
                                key={s.id}
                                onClick={() => handleSelectSession(s.id)}
                                className={`w-full text-left p-3 rounded-lg text-sm truncate transition-colors ${currentSessionId === s.id ? 'bg-slate-800 text-indigo-300' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-300'}`}
                            >
                                {s.title || "New Session"}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col h-full min-w-0">
                {/* Header */}
                <header className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900 shadow-md shrink-0">
                    <div className="flex items-center gap-3">
                        {!sidebarOpen && (
                            <button onClick={() => setSidebarOpen(true)} className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
                                <Menu size={20} />
                            </button>
                        )}
                        <div className="p-2 bg-indigo-600 rounded-lg">
                            <Bot className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                                Agenthic Data Assistant
                            </h1>
                            <p className="text-xs text-slate-500 hidden sm:block">Logged in as {user?.username}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto">
                        {user?.role === 'admin' && (
                            <>
                                <Link to="/admin" className="text-xs sm:text-sm text-emerald-400 hover:text-emerald-300 transition-colors flex items-center gap-1">
                                    <ShieldCheck size={16} /> <span className="hidden sm:inline">Admin</span>
                                </Link>
                                <Link to="/connections" className="text-xs sm:text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-1 border-l border-slate-700 pl-2 sm:pl-4">
                                    <Database size={16} /> <span className="hidden sm:inline">Connections</span>
                                </Link>
                            </>
                        )}
                        <Link to="/dashboard" className="text-xs sm:text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-1 border-l border-slate-700 pl-2 sm:pl-4">
                            <BarChart3 size={16} /> <span className="hidden sm:inline">Dashboard</span>
                        </Link>
                        <button
                            onClick={handleLogout}
                            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors border-l border-slate-700 pl-2 sm:pl-4"
                            title="Logout"
                        >
                            <LogOut className="w-5 h-5" />
                        </button>
                    </div>
                </header>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-6">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`flex max-w-4xl w-full ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} gap-3`}>

                                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-indigo-600' : 'bg-slate-700'}`}>
                                    {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                                </div>

                                <div className={`flex flex-col gap-2 ${msg.role === 'user' ? 'items-end' : 'items-start'} min-w-0 w-full`}>
                                    <div className={`p-4 rounded-2xl shadow-sm overflow-hidden w-full ${msg.role === 'user'
                                        ? 'bg-indigo-600 text-white rounded-tr-sm inline-block w-auto max-w-[85%]'
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
                                        <div className="prose prose-invert max-w-none text-sm leading-relaxed overflow-x-auto">
                                            <ReactMarkdown>
                                                {DOMPurify.sanitize(msg.content)}
                                            </ReactMarkdown>
                                        </div>
                                    </div>

                                    {/* Action row (Feedback + Metadata toggle) */}
                                    {msg.role === 'assistant' && !msg.isPending && (
                                        <div className="flex items-center gap-4 mt-1">
                                            {(msg.llm_used || msg.sql_query || msg.retrieved_docs || msg.reasoning) && (
                                                <button 
                                                    onClick={() => toggleMetadata(idx)}
                                                    className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                                                >
                                                    <Info size={12} />
                                                    <span>Details</span>
                                                    {expandedMetaIndexes[idx] ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                                </button>
                                            )}
                                            {/* HITL Feedback Buttons */}
                                            <div className="flex items-center gap-1">
                                                 <button 
                                                    onClick={() => handleFeedback(idx, msg.id, 1)}
                                                    className={`p-1 rounded transition-colors ${msg.feedback === 1 ? 'text-emerald-400 bg-emerald-400/10' : 'text-slate-500 hover:text-slate-300'}`}
                                                    title="Good Response"
                                                 >
                                                     <ThumbsUp size={14} />
                                                 </button>
                                                 <button 
                                                    onClick={() => handleFeedback(idx, msg.id, -1)}
                                                    className={`p-1 rounded transition-colors ${msg.feedback === -1 ? 'text-rose-400 bg-rose-400/10' : 'text-slate-500 hover:text-slate-300'}`}
                                                    title="Bad Response"
                                                 >
                                                     <ThumbsDown size={14} />
                                                 </button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Metadata Dropdown */}
                                    {expandedMetaIndexes[idx] && (msg.llm_used || msg.sql_query || msg.retrieved_docs || msg.reasoning) && (
                                        <div className="w-full mt-2 p-3 bg-slate-900 border border-slate-700 rounded-lg text-xs font-mono text-slate-400 space-y-3 max-w-full overflow-hidden">
                                            {msg.reasoning && (
                                                <div className="flex gap-2 flex-col">
                                                    <span className="text-slate-500">Agent Reasoning:</span>
                                                    <pre className="whitespace-pre-wrap break-all text-slate-300 bg-slate-950 p-2 rounded border border-slate-800">
                                                        {msg.reasoning}
                                                    </pre>
                                                </div>
                                            )}
                                            {msg.llm_used && (
                                                <div className="flex gap-2 items-center">
                                                    <span className="text-slate-500 min-w-16">LLM:</span>
                                                    <span className="text-indigo-400 font-semibold">{msg.llm_used}</span>
                                                </div>
                                            )}
                                            {msg.retrieved_docs && (
                                                <div className="flex gap-2 flex-col">
                                                    <span className="text-slate-500">RAG Sources:</span>
                                                    <ul className="list-disc list-inside pl-2 text-emerald-400">
                                                        {msg.retrieved_docs.map((doc, i) => {
                                                            const filename = doc.split(/[/\\]/).pop();
                                                            return <li key={i}>{filename}</li>;
                                                        })}
                                                    </ul>
                                                </div>
                                            )}
                                            {msg.sql_query && (
                                                <div className="flex gap-2 flex-col">
                                                    <span className="text-slate-500">SQL Executed:</span>
                                                    <pre className="whitespace-pre-wrap break-all text-cyan-400 bg-slate-950 p-2 rounded border border-slate-800">
                                                        {msg.sql_query}
                                                    </pre>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Optional Data Table */}
                                    {msg.data && msg.data.length > 0 && (
                                        <PaginatedTable data={msg.data} />
                                    )}
                                    {msg.data && msg.data.length === 0 && (
                                        <div className="bg-slate-800 rounded-lg p-3 border border-slate-700 text-xs text-slate-400 italic mt-2">
                                            Query returned no results.
                                        </div>
                                    )}

                                    {/* Chart */}
                                    {msg.chart && (
                                        <div className="mt-2 w-full">
                                            <ChartRenderer spec={msg.chart} />
                                        </div>
                                    )}

                                    {/* Self-Correction UI */}
                                    {msg.failed_sql && (
                                        <div className="mt-4 border border-rose-800 rounded-lg overflow-hidden bg-slate-900 w-full">
                                            <div className="bg-rose-950/50 px-4 py-2 text-xs font-semibold text-rose-300 border-b border-rose-800 flex justify-between items-center">
                                                <span>SQL Self-Correction</span>
                                                <span className="text-slate-400 font-normal">Edit & Retry</span>
                                            </div>
                                            <div className="p-4 grid gap-4">
                                                <div>
                                                    <label className="text-xs text-slate-400 uppercase tracking-wider mb-1 block">Failed Query:</label>
                                                    <textarea 
                                                        className="w-full bg-slate-950 text-emerald-400 font-mono text-sm p-3 rounded border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                                                        rows={4}
                                                        value={editingSqlIndexes[idx] !== undefined ? editingSqlIndexes[idx] : msg.failed_sql}
                                                        onChange={(e) => handleSqlCorrectionEdit(idx, e.target.value)}
                                                    />
                                                </div>
                                                {msg.schema_context && (
                                                    <div>
                                                        <label className="text-xs text-slate-400 uppercase tracking-wider mb-1 block">Available Schema:</label>
                                                        <pre className="w-full bg-slate-950 text-slate-300 font-mono text-xs p-3 rounded border border-slate-700 overflow-x-auto max-h-32">
                                                            {msg.schema_context}
                                                        </pre>
                                                    </div>
                                                )}
                                                <div className="flex justify-end">
                                                    <button 
                                                        onClick={() => handleSqlCorrectionSubmit(idx, msg)}
                                                        disabled={loading}
                                                        className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                                                    >
                                                        <Send size={14} /> Execute Fix
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="flex items-center gap-2 bg-slate-800 px-4 py-3 rounded-2xl rounded-tl-sm border border-slate-700 ml-[44px]">
                                <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                                <span className="text-xs font-medium text-slate-300 bg-clip-text text-transparent bg-gradient-to-r from-slate-300 to-indigo-300 animate-pulse">{agentProgress || 'Thinking...'}</span>
                            </div>
                        </div>
                    )}
                    <div ref={scrollRef} className="h-4" />
                </div>

                {/* Input Area */}
                <div className="p-4 border-t border-slate-800 bg-slate-900/80 backdrop-blur-md shrink-0">
                    <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask about sales trends or return policies..."
                            className="w-full bg-slate-950 text-slate-100 border border-slate-700 rounded-xl pl-5 pr-14 py-4 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all shadow-inner placeholder:text-slate-500 text-sm sm:text-base"
                        />
                        <button
                            type="submit"
                            disabled={loading || !input.trim()}
                            className="absolute right-2 top-2 bottom-2 p-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                        >
                            <Send size={18} />
                        </button>
                    </form>
                    <div className="text-center mt-3 text-xs text-slate-500 flex justify-center gap-4">
                        <span className="flex items-center gap-1.5"><Database size={12} className="text-cyan-500" /> SQLite Memory</span>
                        <span className="flex items-center gap-1.5"><FileText size={12} className="text-emerald-500" /> Hybrid RAG</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

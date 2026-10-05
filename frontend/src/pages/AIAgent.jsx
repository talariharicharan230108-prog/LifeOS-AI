import React, { useState, useRef, useEffect } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  ArrowRight,
  CheckCircle,
  Database,
  Cpu,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Wrench,
  AlertTriangle
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import * as api from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

export default function AIAgent() {
  const { data, refreshData, geminiInfo } = useApp();
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Hello! I am **LifeOS AI**, your personal academic and productivity planning agent. I am directly connected to your stored tasks (${data?.tasks?.length || 0}), subjects (${data?.subjects?.length || 0}), daily routine, and deadlines. How can I assist you today?`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      transparency: null,
      inferences: []
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showTransparency, setShowTransparency] = useState(true);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const quickPrompts = [
    'What should I do today?',
    'Create my plan for today',
    'Summarize my pending tasks',
    'What should I study today?',
    'Show my upcoming deadlines'
  ];

  const handleSend = async (messageText) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || isTyping) return;

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      const res = await api.sendAgentMessage(textToSend);
      const assistantMsg = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: res.response || res.response_text || res.message || 'I have processed your request.',
        thought: res.thought,
        action: res.action,
        actionResult: res.action_result,
        inferences: res.inferences || [],
        transparency: res.transparency,
        isLiveGemini: res.is_live_gemini,
        fallbackOccurred: res.fallback_occurred,
        activeModel: res.active_model,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // If an action updated tasks or schedule, refresh state
      if (res.action && res.action !== 'none') {
        refreshData();
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `ai-err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ Failed to communicate with agent: ${err.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)] animate-in fade-in duration-200">
      {/* Top Banner: Architecture & Transparency Toggle */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm mb-4 gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                LifeOS Personal Assistant
              </h2>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                geminiInfo?.configured
                  ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300'
                  : 'bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${geminiInfo?.configured ? 'bg-emerald-500 animate-pulse' : 'bg-indigo-500'}`} />
                {geminiInfo?.configured ? 'Online Assistant' : 'Local Assistant'}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Personalized planning, holiday tracking, task management, and academic assistance.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowTransparency(!showTransparency)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 transition"
        >
          <HelpCircle className="w-3.5 h-3.5 text-indigo-500" />
          <span>How LifeOS AI Works</span>
          {showTransparency ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Architecture Transparency Drawer */}
      {showTransparency && (
        <div className="mb-4 p-4 rounded-2xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-200/60 dark:border-indigo-800/40 text-xs">
          <h4 className="font-bold text-indigo-900 dark:text-indigo-300 mb-2 flex items-center gap-1.5">
            <Cpu className="w-4 h-4 text-indigo-600" />
            AI Agent Architecture Pipeline (Evaluation Transparency)
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-center">
            <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-indigo-100 dark:border-indigo-900/60">
              <span className="font-bold text-slate-700 dark:text-slate-300 block">1. User Request</span>
              <span className="text-[10px] text-slate-500">Natural prompt</span>
            </div>
            <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-indigo-100 dark:border-indigo-900/60">
              <span className="font-bold text-slate-700 dark:text-slate-300 block">2. Understand</span>
              <span className="text-[10px] text-slate-500">Intent & slots</span>
            </div>
            <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-indigo-100 dark:border-indigo-900/60">
              <span className="font-bold text-slate-700 dark:text-slate-300 block">3. Retrieve Data</span>
              <span className="text-[10px] text-slate-500">Tasks, routine, exam</span>
            </div>
            <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-indigo-100 dark:border-indigo-900/60">
              <span className="font-bold text-slate-700 dark:text-slate-300 block">4. Gemini Reason</span>
              <span className="text-[10px] text-slate-500">Inference rules</span>
            </div>
            <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-indigo-100 dark:border-indigo-900/60">
              <span className="font-bold text-slate-700 dark:text-slate-300 block">5. Tool Action</span>
              <span className="text-[10px] text-slate-500">Add / schedule</span>
            </div>
            <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-indigo-100 dark:border-indigo-900/60">
              <span className="font-bold text-slate-700 dark:text-slate-300 block">6. Response</span>
              <span className="text-[10px] text-slate-500">Action confirmation</span>
            </div>
          </div>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 rounded-2xl bg-slate-100/50 dark:bg-slate-900/40 border border-slate-200/80 dark:border-slate-800">
        {messages.map((m) => {
          const isUser = m.role === 'user';
          return (
            <div
              key={m.id}
              className={`flex gap-3 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
            >
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                  isUser
                    ? 'bg-slate-800 dark:bg-slate-700 text-white'
                    : 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                }`}
              >
                {isUser ? <span className="text-xs font-bold">U</span> : <Bot className="w-4 h-4" />}
              </div>

              <div
                className={`rounded-2xl p-4 text-xs leading-relaxed ${
                  isUser
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 text-slate-800 dark:text-slate-200 shadow-sm'
                }`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>

                <span className={`block text-[9px] mt-1 text-right ${isUser ? 'text-indigo-200' : 'text-slate-400'}`}>
                  {m.timestamp}
                </span>
              </div>
            </div>
          );
        })}

        {isTyping && (
          <div className="flex gap-3 max-w-sm mr-auto">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shrink-0">
              <Bot className="w-4 h-4 animate-pulse" />
            </div>
            <div className="p-3.5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-500 flex items-center gap-2">
              <LoadingSpinner size="sm" text="" />
              <span>LifeOS AI is retrieving data & reasoning...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Prompts */}
      <div className="py-2 flex items-center gap-2 overflow-x-auto no-scrollbar">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider shrink-0">
          Suggested:
        </span>
        {quickPrompts.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(p)}
            className="text-xs px-3 py-1 rounded-full bg-white dark:bg-slate-900 hover:bg-indigo-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 font-medium whitespace-nowrap transition active:scale-95"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Chat Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center gap-2 pt-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask LifeOS AI: 'Create study plan for DBMS tomorrow' or 'What should I do today?'..."
          className="flex-1 px-4 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
        />
        <button
          type="submit"
          disabled={!input.trim() || isTyping}
          className="px-5 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition shadow-md shadow-indigo-600/20 active:scale-95 disabled:opacity-50 flex items-center gap-2"
        >
          <span>Send</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
}

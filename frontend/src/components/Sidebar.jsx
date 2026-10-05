import React from 'react';
import {
  LayoutDashboard,
  Bot,
  CheckSquare,
  Clock,
  Calendar,
  GraduationCap,
  FileText,
  Target,
  Cpu,
  Settings,
  Sparkles,
  Zap,
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function Sidebar() {
  const { activeTab, setActiveTab, data, geminiInfo } = useApp();

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'agent', label: 'AI Agent', icon: Bot, badge: 'Agent' },
    { id: 'tasks', label: 'Tasks', icon: CheckSquare, count: data?.tasks?.filter(t => !t.completed).length },
    { id: 'calendar', label: 'Calendar', icon: Calendar },
    { id: 'academic', label: 'Academic', icon: GraduationCap },
    { id: 'documents', label: 'Documents', icon: FileText, count: data?.documents?.length },
    { id: 'goals', label: 'Goals', icon: Target },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-white/90 dark:bg-slate-900/90 border-r border-slate-200/80 dark:border-slate-800/80 flex flex-col h-screen sticky top-0 transition-colors select-none z-40">
      {/* Brand Header */}
      <div className="p-5 flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="font-bold text-base tracking-tight text-slate-900 dark:text-white leading-none">
              LifeOS
            </h2>
            <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-600 dark:text-indigo-400">
              AI Study Assistant
            </span>
          </div>
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 dark:shadow-indigo-900/30'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400 dark:text-slate-500'}`} />
                <span>{item.label}</span>
              </div>
              <div className="flex items-center gap-1.5">
                {item.badge && (
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase ${
                      isActive
                        ? 'bg-indigo-700 text-indigo-100'
                        : 'bg-indigo-50 dark:bg-indigo-950/80 text-indigo-600 dark:text-indigo-400'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
                {typeof item.count === 'number' && item.count > 0 && (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full font-medium ${
                      isActive ? 'bg-indigo-500/40 text-white' : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                    }`}
                  >
                    {item.count}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </nav>

      {/* AI Status Badge */}
      <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-950/40">
        <div className="flex items-center justify-between text-[11px]">
          <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
            <span className={`w-2 h-2 rounded-full ${geminiInfo?.configured ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'}`} />
            Gemini AI
          </span>
          <span className="font-medium text-slate-700 dark:text-slate-300">
            {geminiInfo?.configured ? 'Active' : 'Offline / Rules'}
          </span>
        </div>
      </div>
    </aside>
  );
}

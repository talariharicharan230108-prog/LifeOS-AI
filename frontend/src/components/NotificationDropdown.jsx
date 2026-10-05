import React from 'react';
import { Bell, AlertTriangle, CheckCircle, Info, Calendar } from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function NotificationDropdown({ isOpen, onClose }) {
  const { notifications, setActiveTab } = useApp();

  if (!isOpen) return null;

  const getIcon = (type) => {
    switch (type) {
      case 'critical':
        return <AlertTriangle className="w-4 h-4 text-rose-500" />;
      case 'warning':
        return <Calendar className="w-4 h-4 text-amber-500" />;
      default:
        return <Info className="w-4 h-4 text-indigo-500" />;
    }
  };

  return (
    <div
      className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 py-3 z-50 animate-in fade-in zoom-in-95 duration-150"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between px-4 pb-2 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Notifications</h4>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-medium">
          {notifications.length} Active
        </span>
      </div>

      <div className="max-h-72 overflow-y-auto divide-y divide-slate-50 dark:divide-slate-800/60">
        {notifications.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-400">
            No active alerts or approaching deadlines. All clear!
          </div>
        ) : (
          notifications.map((n) => (
            <div
              key={n.id}
              onClick={() => {
                if (n.tab) setActiveTab(n.tab);
                onClose();
              }}
              className="p-3.5 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition flex items-start gap-3"
            >
              <div className="mt-0.5">{getIcon(n.type)}</div>
              <div className="flex-1">
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">{n.title}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{n.message}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

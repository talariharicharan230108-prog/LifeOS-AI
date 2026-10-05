import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppProvider, useApp } from './context/AppContext';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import OnboardingModal from './components/OnboardingModal';
import LoadingSpinner from './components/LoadingSpinner';

// Pages
import AuthPage from './pages/AuthPage';
import Dashboard from './pages/Dashboard';
import AIAgent from './pages/AIAgent';
import Tasks from './pages/Tasks';
import CalendarPage from './pages/Calendar';
import Academic from './pages/Academic';
import Documents from './pages/Documents';
import Goals from './pages/Goals';
import Settings from './pages/Settings';

function MainLayout() {
  const { data, activeTab, loading, searchQuery, setSearchQuery, setActiveTab } = useApp();

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'agent':
        return <AIAgent />;
      case 'tasks':
        return <Tasks />;
      case 'calendar':
        return <CalendarPage />;
      case 'academic':
        return <Academic />;
      case 'documents':
        return <Documents />;
      case 'goals':
        return <Goals />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  // Global search match computation
  const searchResults = React.useMemo(() => {
    if (!searchQuery.trim()) return null;
    const q = searchQuery.toLowerCase();
    const tasks = (data?.tasks || []).filter(
      (t) => t.title?.toLowerCase().includes(q) || t.subject?.toLowerCase().includes(q)
    );
    const subjects = (data?.subjects || []).filter(
      (s) => s.name?.toLowerCase().includes(q) || s.teacher?.toLowerCase().includes(q)
    );
    const goals = (data?.goals || []).filter(
      (g) => g.title?.toLowerCase().includes(q) || g.category?.toLowerCase().includes(q)
    );
    const docs = (data?.documents || []).filter((d) => d.name?.toLowerCase().includes(q));
    const events = (data?.events || []).filter(
      (e) => e.title?.toLowerCase().includes(q) || e.subject?.toLowerCase().includes(q)
    );

    return { tasks, subjects, goals, docs, events };
  }, [searchQuery, data]);

  const { user: authUser } = useAuth();
  const [showOnboarding, setShowOnboarding] = React.useState(false);

  React.useEffect(() => {
    if (!authUser?.id) {
      setShowOnboarding(false);
      return;
    }

    if (loading) {
      return;
    }

    const completed = data?.settings?.onboardingCompleted === true;
    setShowOnboarding(!completed);
  }, [authUser?.id, loading, data?.settings?.onboardingCompleted]);

  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <LoadingSpinner size="lg" text="Loading LifeOS personal workspace..." />
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      {/* First-time Real Onboarding Wizard */}
      <OnboardingModal isOpen={showOnboarding} />

      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Header />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 relative">
          {/* Global Search Results Overlay */}
          {searchResults && (
            <div className="mb-6 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-900 shadow-xl space-y-4 animate-in fade-in">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                <h3 className="text-sm font-bold text-indigo-600 dark:text-indigo-400">
                  Search Results for "{searchQuery}"
                </h3>
                <button
                  onClick={() => setSearchQuery('')}
                  className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  Close Search
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
                {/* Matched Tasks */}
                <div>
                  <h4 className="font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Tasks ({searchResults.tasks.length})
                  </h4>
                  {searchResults.tasks.length === 0 ? (
                    <p className="text-[11px] text-slate-400">No matching tasks</p>
                  ) : (
                    searchResults.tasks.map((t) => (
                      <div
                        key={t.id}
                        onClick={() => {
                          setActiveTab('tasks');
                          setSearchQuery('');
                        }}
                        className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 mb-1 cursor-pointer hover:bg-indigo-50 dark:hover:bg-slate-800"
                      >
                        <p className="font-semibold text-slate-800 dark:text-slate-200">{t.title}</p>
                        <p className="text-[10px] text-slate-400">Due: {t.deadline || 'None'}</p>
                      </div>
                    ))
                  )}
                </div>

                {/* Matched Subjects */}
                <div>
                  <h4 className="font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Subjects ({searchResults.subjects.length})
                  </h4>
                  {searchResults.subjects.length === 0 ? (
                    <p className="text-[11px] text-slate-400">No matching subjects</p>
                  ) : (
                    searchResults.subjects.map((s) => (
                      <div
                        key={s.id}
                        onClick={() => {
                          setActiveTab('academic');
                          setSearchQuery('');
                        }}
                        className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 mb-1 cursor-pointer hover:bg-indigo-50 dark:hover:bg-slate-800"
                      >
                        <p className="font-semibold text-slate-800 dark:text-slate-200">{s.name}</p>
                        <p className="text-[10px] text-slate-400">{s.teacher || 'Course'}</p>
                      </div>
                    ))
                  )}
                </div>

                {/* Matched Goals & Documents */}
                <div>
                  <h4 className="font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Goals & Documents ({searchResults.goals.length + searchResults.docs.length})
                  </h4>
                  {searchResults.goals.concat(searchResults.docs).length === 0 ? (
                    <p className="text-[11px] text-slate-400">No matching items</p>
                  ) : (
                    searchResults.goals.map((g) => (
                      <div
                        key={g.id}
                        onClick={() => {
                          setActiveTab('goals');
                          setSearchQuery('');
                        }}
                        className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 mb-1 cursor-pointer hover:bg-indigo-50 dark:hover:bg-slate-800"
                      >
                        <p className="font-semibold text-slate-800 dark:text-slate-200">{g.title}</p>
                        <p className="text-[10px] text-slate-400">{g.progress}% done</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {renderActivePage()}
        </main>
      </div>
    </div>
  );
}

function AuthenticatedApp() {
  const { user, isAuthenticated, authLoading, loading } = useAuth();
  const isLoading = authLoading !== undefined ? authLoading : loading;

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-950 text-slate-100">
        <LoadingSpinner size="lg" text="Authenticating LifeOS workspace..." />
      </div>
    );
  }

  if (!isAuthenticated && !user) {
    return <AuthPage />;
  }

  return (
    <AppProvider>
      <MainLayout />
    </AppProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}

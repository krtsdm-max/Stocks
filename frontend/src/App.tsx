import { useState } from 'react';
import { LayoutDashboard, MessageSquare, Users, Settings, TrendingUp } from 'lucide-react';
import clsx from 'clsx';
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { ExpertsPage } from './pages/ExpertsPage';
import { SettingsPage } from './pages/SettingsPage';

type Page = 'dashboard' | 'chat' | 'experts' | 'settings';

const NAV_ITEMS: { id: Page; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Portfolio', icon: <LayoutDashboard size={18} /> },
  { id: 'chat', label: 'Committee Chat', icon: <MessageSquare size={18} /> },
  { id: 'experts', label: 'Expert Track Record', icon: <Users size={18} /> },
  { id: 'settings', label: 'Settings', icon: <Settings size={18} /> },
];

export default function App() {
  const [page, setPage] = useState<Page>('dashboard');
  const [chatTicker, setChatTicker] = useState<string | undefined>(undefined);

  const navigate = (p: Page, ticker?: string) => {
    setPage(p);
    if (ticker) setChatTicker(ticker);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-56 bg-blue-950 text-white flex flex-col z-20 shadow-xl">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-blue-800">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <TrendingUp size={18} />
          </div>
          <div>
            <p className="font-bold text-sm leading-tight">Portfolio</p>
            <p className="text-blue-400 text-xs">Advisor AI</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              onClick={() => navigate(item.id)}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all font-medium',
                page === item.id
                  ? 'bg-blue-700 text-white'
                  : 'text-blue-200 hover:bg-blue-800 hover:text-white',
              )}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>

        <div className="px-5 py-4 border-t border-blue-800">
          <p className="text-blue-400 text-xs">Investment Committee AI</p>
          <p className="text-blue-500 text-xs">Victoria · Marcus · Sophie</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-56 min-h-screen">
        <div className="max-w-6xl mx-auto px-6 py-6">
          {page === 'dashboard' && (
            <DashboardPage onNavigateToChat={(ticker) => navigate('chat', ticker)} />
          )}
          {page === 'chat' && <ChatPage defaultTicker={chatTicker} />}
          {page === 'experts' && <ExpertsPage />}
          {page === 'settings' && <SettingsPage />}
        </div>
      </main>
    </div>
  );
}

import { useState, useEffect, useCallback } from 'react';
import { Plus, RefreshCw } from 'lucide-react';
import { getPortfolio, getSettings, refreshRecommendations } from '../services/api';
import type { Portfolio, UserSettings, PortfolioPosition } from '../types';
import { PortfolioHeader } from '../components/Dashboard/PortfolioHeader';
import { PositionsTable } from '../components/Dashboard/PositionsTable';
import { AddPositionModal } from '../components/Portfolio/AddPositionModal';
import { EditPositionModal } from '../components/Portfolio/EditPositionModal';
import { PositionDetailCard } from '../components/Experts/PositionDetailCard';
import { LoadingSpinner } from '../components/Common/LoadingSpinner';

type View = 'dashboard' | 'detail';

interface Props {
  onNavigateToChat?: (ticker?: string) => void;
}

export function DashboardPage({ onNavigateToChat }: Props) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<View>('dashboard');
  const [selectedPositionId, setSelectedPositionId] = useState<number | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editPosition, setEditPosition] = useState<PortfolioPosition | null>(null);

  const load = useCallback(async () => {
    try {
      const [p, s] = await Promise.all([getPortfolio(), getSettings()]);
      setPortfolio(p);
      setSettings(s);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // Auto-refresh every 5 minutes
    const interval = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [load]);

  const handleSelectPosition = (id: number) => {
    setSelectedPositionId(id);
    setView('detail');
  };

  const handleRefreshPosition = async (id: number) => {
    await refreshRecommendations(id);
    await load();
  };

  const selectedPosition = portfolio?.positions.find(p => p.id === selectedPositionId);

  if (loading) return <LoadingSpinner size="lg" />;
  if (!portfolio || !settings) return null;

  if (view === 'detail' && selectedPositionId && selectedPosition) {
    return (
      <PositionDetailCard
        positionId={selectedPositionId}
        position={selectedPosition}
        onBack={() => setView('dashboard')}
        onEdit={() => setEditPosition(selectedPosition)}
      />
    );
  }

  return (
    <div>
      <PortfolioHeader portfolio={portfolio} riskProfile={settings.risk_profile} />

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          Positions <span className="text-gray-400 font-normal text-sm">({portfolio.positions.length})</span>
        </h2>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="flex items-center gap-1.5 text-sm border border-gray-300 rounded-lg px-3 py-1.5 hover:bg-gray-50 text-gray-600"
          >
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 text-sm bg-blue-600 text-white rounded-lg px-3 py-1.5 hover:bg-blue-700"
          >
            <Plus size={14} /> Add Position
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <PositionsTable
          positions={portfolio.positions}
          onSelectPosition={handleSelectPosition}
          onRefreshPosition={handleRefreshPosition}
        />
      </div>

      {showAddModal && (
        <AddPositionModal
          onClose={() => setShowAddModal(false)}
          onAdded={() => { load(); setShowAddModal(false); }}
        />
      )}

      {editPosition && (
        <EditPositionModal
          position={editPosition}
          onClose={() => setEditPosition(null)}
          onUpdated={() => { load(); setEditPosition(null); }}
          onDeleted={() => { load(); setEditPosition(null); }}
        />
      )}
    </div>
  );
}

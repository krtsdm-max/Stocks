import { useState } from 'react';
import { TrendingUp, TrendingDown, Clock, Shield, Pencil, Check, X } from 'lucide-react';
import type { Portfolio } from '../../types';
import { formatCurrency } from '../Common/NumberDisplay';

const RISK_LABELS: Record<string, string> = {
  conservative: 'Conservative',
  balanced: 'Balanced',
  aggressive: 'Aggressive',
};

const RISK_COLORS: Record<string, string> = {
  conservative: 'bg-blue-100 text-blue-700',
  balanced: 'bg-yellow-100 text-yellow-700',
  aggressive: 'bg-red-100 text-red-700',
};

interface Props {
  portfolio: Portfolio;
  riskProfile: string;
  onCashUpdate: (amount: number) => Promise<void>;
}

export function PortfolioHeader({ portfolio, riskProfile, onCashUpdate }: Props) {
  const [editingCash, setEditingCash] = useState(false);
  const [cashInput, setCashInput] = useState('');
  const [savingCash, setSavingCash] = useState(false);

  const dayPositive = portfolio.day_pnl >= 0;
  const updatedAt = new Date(portfolio.last_updated).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  const startEditCash = () => {
    setCashInput(portfolio.cash.toFixed(2));
    setEditingCash(true);
  };

  const cancelEditCash = () => {
    setEditingCash(false);
    setCashInput('');
  };

  const saveCash = async () => {
    const value = parseFloat(cashInput.replace(/,/g, ''));
    if (isNaN(value) || value < 0) return;
    setSavingCash(true);
    try {
      await onCashUpdate(value);
      setEditingCash(false);
    } finally {
      setSavingCash(false);
    }
  };

  const handleCashKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') saveCash();
    if (e.key === 'Escape') cancelEditCash();
  };

  return (
    <div className="bg-gradient-to-r from-blue-900 to-blue-800 rounded-xl p-6 text-white mb-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
        {/* Left: NAV breakdown */}
        <div>
          <p className="text-blue-200 text-sm font-medium uppercase tracking-wider mb-1">
            Portfolio Value (NAV)
          </p>
          <p className="text-4xl font-bold tabular-nums">
            {formatCurrency(portfolio.nav)}
          </p>
          <div className="flex items-center gap-3 mt-2">
            <span className={`flex items-center gap-1 text-sm font-medium ${dayPositive ? 'text-green-300' : 'text-red-300'}`}>
              {dayPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {dayPositive ? '+' : ''}{formatCurrency(portfolio.day_pnl)} ({dayPositive ? '+' : ''}{portfolio.day_pnl_pct.toFixed(2)}%) today
            </span>
          </div>

          {/* Invested + Cash row */}
          <div className="flex items-center gap-4 mt-3">
            <span className="text-blue-300 text-sm">
              Invested: <span className="text-white font-medium">{formatCurrency(portfolio.invested_value)}</span>
            </span>
            <span className="text-blue-500 text-xs">|</span>
            <span className="text-blue-300 text-sm flex items-center gap-1.5">
              Cash:&nbsp;
              {editingCash ? (
                <span className="flex items-center gap-1">
                  <span className="text-white">$</span>
                  <input
                    autoFocus
                    type="number"
                    min="0"
                    step="0.01"
                    value={cashInput}
                    onChange={e => setCashInput(e.target.value)}
                    onKeyDown={handleCashKeyDown}
                    className="w-28 bg-blue-700/60 border border-blue-400 rounded px-2 py-0.5 text-white text-sm tabular-nums focus:outline-none focus:border-blue-300"
                  />
                  <button
                    onClick={saveCash}
                    disabled={savingCash}
                    className="p-0.5 rounded hover:bg-blue-600 text-green-300 hover:text-green-200 disabled:opacity-50"
                    title="Save"
                  >
                    <Check size={14} />
                  </button>
                  <button
                    onClick={cancelEditCash}
                    className="p-0.5 rounded hover:bg-blue-600 text-red-300 hover:text-red-200"
                    title="Cancel"
                  >
                    <X size={14} />
                  </button>
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <span className="text-white font-medium">{formatCurrency(portfolio.cash)}</span>
                  <button
                    onClick={startEditCash}
                    className="p-0.5 rounded hover:bg-blue-700 text-blue-400 hover:text-blue-200 transition-colors"
                    title="Edit cash balance"
                  >
                    <Pencil size={12} />
                  </button>
                </span>
              )}
            </span>
          </div>
        </div>

        {/* Right: Risk profile + Total P&L */}
        <div className="flex flex-col items-end gap-3">
          <div className={`px-3 py-1.5 rounded-lg text-sm font-medium ${RISK_COLORS[riskProfile] ?? 'bg-gray-100 text-gray-700'}`}>
            <Shield size={14} className="inline mr-1" />
            {RISK_LABELS[riskProfile] ?? riskProfile}
          </div>

          <div className="text-right">
            <p className="text-blue-300 text-xs">Total P&L</p>
            <p className={`text-lg font-semibold ${portfolio.total_pnl >= 0 ? 'text-green-300' : 'text-red-300'}`}>
              {portfolio.total_pnl >= 0 ? '+' : ''}{formatCurrency(portfolio.total_pnl)}
              <span className="text-sm ml-1">({portfolio.total_pnl_pct >= 0 ? '+' : ''}{portfolio.total_pnl_pct.toFixed(2)}%)</span>
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-4 pt-4 border-t border-blue-700">
        <span className="text-blue-300 text-xs flex items-center gap-1">
          <Clock size={12} />
          Updated: {updatedAt} UTC
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${portfolio.market_open ? 'bg-green-500/20 text-green-300' : 'bg-gray-500/20 text-gray-300'}`}>
          {portfolio.market_open ? '● Market Open' : '● Market Closed'}
        </span>
        <span className="text-blue-300 text-xs">
          {portfolio.positions_count} positions
        </span>
      </div>
    </div>
  );
}

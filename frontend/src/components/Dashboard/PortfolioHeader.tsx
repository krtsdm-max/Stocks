import { TrendingUp, TrendingDown, Clock, Shield } from 'lucide-react';
import type { Portfolio } from '../../types';
import { PnlDisplay, formatCurrency } from '../Common/NumberDisplay';

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
}

export function PortfolioHeader({ portfolio, riskProfile }: Props) {
  const dayPositive = portfolio.day_pnl >= 0;
  const updatedAt = new Date(portfolio.last_updated).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  return (
    <div className="bg-gradient-to-r from-blue-900 to-blue-800 rounded-xl p-6 text-white mb-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
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
        </div>

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

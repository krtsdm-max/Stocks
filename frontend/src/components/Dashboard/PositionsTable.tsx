import { useState } from 'react';
import { ChevronDown, ChevronRight, RefreshCw, BarChart2 } from 'lucide-react';
import type { PortfolioPosition } from '../../types';
import { ActionBadge, ConsensusBadge } from '../Common/Badge';
import { formatCurrency, formatPct } from '../Common/NumberDisplay';
import { InlineSpinner } from '../Common/LoadingSpinner';

interface Props {
  positions: PortfolioPosition[];
  onSelectPosition: (id: number) => void;
  onRefreshPosition: (id: number) => Promise<void>;
}

const EXPERT_LABELS: Record<string, string> = {
  value: 'V',
  momentum: 'M',
  risk: 'R',
};

const EXPERT_COLORS: Record<string, string> = {
  value: 'bg-purple-100 text-purple-700',
  momentum: 'bg-blue-100 text-blue-700',
  risk: 'bg-orange-100 text-orange-700',
};

export function PositionsTable({ positions, onSelectPosition, onRefreshPosition }: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [refreshingId, setRefreshingId] = useState<number | null>(null);

  const handleRefresh = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setRefreshingId(id);
    try {
      await onRefreshPosition(id);
    } finally {
      setRefreshingId(null);
    }
  };

  if (positions.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <BarChart2 size={48} className="mx-auto mb-3 text-gray-300" />
        <p className="font-medium">No positions yet</p>
        <p className="text-sm mt-1">Add your first position to get started.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-gray-500 text-xs uppercase tracking-wider">
            <th className="text-left py-3 px-4 font-medium w-8"></th>
            <th className="text-left py-3 px-4 font-medium">Ticker</th>
            <th className="text-right py-3 px-4 font-medium">Price</th>
            <th className="text-right py-3 px-4 font-medium">Day</th>
            <th className="text-right py-3 px-4 font-medium">Weight</th>
            <th className="text-right py-3 px-4 font-medium">P&L</th>
            <th className="text-left py-3 px-4 font-medium">Consensus</th>
            <th className="text-left py-3 px-4 font-medium">Experts</th>
            <th className="text-right py-3 px-4 font-medium w-20"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {positions.map(pos => {
            const isExpanded = expandedId === pos.id;
            const consensus = pos.latest_consensus;
            const action = consensus?.aggregated_action;
            const dayPositive = (pos.day_change ?? 0) >= 0;
            const pnlPositive = pos.total_pnl >= 0;

            return (
              <>
                <tr
                  key={pos.id}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => setExpandedId(isExpanded ? null : pos.id)}
                >
                  <td className="py-3 px-4 text-gray-400">
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </td>
                  <td className="py-3 px-4">
                    <button
                      className="font-bold text-gray-900 hover:text-blue-600 transition-colors"
                      onClick={(e) => { e.stopPropagation(); onSelectPosition(pos.id); }}
                    >
                      {pos.ticker}
                    </button>
                    <div className="text-xs text-gray-400">{pos.quantity.toLocaleString()} shares</div>
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums font-medium text-gray-900">
                    {pos.current_price != null ? formatCurrency(pos.current_price) : '—'}
                  </td>
                  <td className={`py-3 px-4 text-right tabular-nums text-xs ${dayPositive ? 'text-green-600' : 'text-red-600'}`}>
                    {pos.day_change != null ? (
                      <>
                        {dayPositive ? '+' : ''}{pos.day_change.toFixed(2)}<br />
                        <span>({dayPositive ? '+' : ''}{pos.day_change_pct?.toFixed(2)}%)</span>
                      </>
                    ) : '—'}
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums text-gray-600">
                    {pos.portfolio_weight.toFixed(1)}%
                  </td>
                  <td className={`py-3 px-4 text-right tabular-nums ${pnlPositive ? 'text-green-600' : 'text-red-600'}`}>
                    {pnlPositive ? '+' : ''}{formatCurrency(pos.total_pnl)}<br />
                    <span className="text-xs">({pnlPositive ? '+' : ''}{pos.total_pnl_pct.toFixed(2)}%)</span>
                  </td>
                  <td className="py-3 px-4">
                    {action ? (
                      <div className="flex flex-col gap-1">
                        <ActionBadge action={action} />
                        {consensus && <ConsensusBadge level={consensus.consensus_level} />}
                      </div>
                    ) : (
                      <span className="text-gray-400 text-xs">No data</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {consensus && (
                      <div className="flex gap-1">
                        {Object.entries(consensus.expert_votes).map(([type, vote]) => (
                          <span key={type}
                            className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${EXPERT_COLORS[type]}`}
                            title={`${type}: ${vote.action}`}
                          >
                            {EXPERT_LABELS[type]}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      className="text-gray-400 hover:text-blue-600 transition-colors p-1 rounded"
                      onClick={(e) => handleRefresh(e, pos.id)}
                      title="Refresh recommendations"
                    >
                      {refreshingId === pos.id ? <InlineSpinner /> : <RefreshCw size={14} />}
                    </button>
                  </td>
                </tr>

                {isExpanded && consensus && (
                  <tr key={`expanded-${pos.id}`} className="bg-blue-50/50">
                    <td colSpan={9} className="px-8 py-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {Object.entries(consensus.expert_votes).map(([type, vote]) => (
                          <div key={type} className="bg-white rounded-lg p-3 border border-blue-100 shadow-sm">
                            <div className="flex items-center justify-between mb-2">
                              <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded ${EXPERT_COLORS[type]}`}>
                                {type === 'value' ? 'Value Investor' : type === 'momentum' ? 'Momentum Trader' : 'Risk Manager'}
                              </span>
                              <ActionBadge action={vote.action} />
                            </div>
                            <p className="text-xs text-gray-600 leading-relaxed line-clamp-4">{vote.reasoning}</p>
                            <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
                              <span>Confidence: {vote.confidence_level}%</span>
                              {vote.target_price && <span>Target: {formatCurrency(vote.target_price)}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 flex gap-2">
                        <button
                          className="text-xs text-blue-600 hover:underline font-medium"
                          onClick={() => onSelectPosition(pos.id)}
                        >
                          View full analysis →
                        </button>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

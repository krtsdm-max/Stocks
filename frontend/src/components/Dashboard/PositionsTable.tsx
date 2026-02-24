import { useState } from 'react';
import { ChevronDown, ChevronRight, RefreshCw, BarChart2, TrendingDown } from 'lucide-react';
import type { PortfolioPosition, AggregatedPosition, ConsensusDecision } from '../../types';
import { ActionBadge, ConsensusBadge } from '../Common/Badge';
import { formatCurrency, formatPct } from '../Common/NumberDisplay';
import { InlineSpinner } from '../Common/LoadingSpinner';

interface Props {
  positions: PortfolioPosition[];
  onSelectPosition: (id: number) => void;
  onRefreshPosition: (ids: number[]) => Promise<void>;
  onSellTicker: (ticker: string, totalQuantity: number, currentPrice?: number) => void;
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

function groupPositions(positions: PortfolioPosition[]): AggregatedPosition[] {
  const groups = new Map<string, PortfolioPosition[]>();
  for (const pos of positions) {
    const list = groups.get(pos.ticker) ?? [];
    list.push(pos);
    groups.set(pos.ticker, list);
  }

  return Array.from(groups.entries()).map(([ticker, subs]) => {
    const totalQty = subs.reduce((s, p) => s + p.quantity, 0);
    const weightedAvg = subs.reduce((s, p) => s + p.quantity * p.average_purchase_price, 0) / totalQty;
    const totalValue = subs.reduce((s, p) => s + (p.total_value ?? 0), 0);
    const totalPnl = subs.reduce((s, p) => s + (p.total_pnl ?? 0), 0);
    const totalWeight = subs.reduce((s, p) => s + (p.portfolio_weight ?? 0), 0);
    const currentPrice = subs[0].current_price;
    const totalPnlPct = currentPrice && weightedAvg
      ? ((currentPrice - weightedAvg) / weightedAvg) * 100
      : 0;
    // Use consensus from the largest sub-position
    const byQty = [...subs].sort((a, b) => b.quantity - a.quantity);
    const latestConsensus = byQty.find(p => p.latest_consensus)?.latest_consensus;

    return {
      ticker,
      ids: subs.map(p => p.id),
      quantity: totalQty,
      average_purchase_price: weightedAvg,
      current_price: currentPrice,
      day_change: subs[0].day_change,
      day_change_pct: subs[0].day_change_pct,
      total_value: totalValue,
      total_pnl: totalPnl,
      total_pnl_pct: totalPnlPct,
      portfolio_weight: totalWeight,
      latest_consensus: latestConsensus,
      sub_positions: subs,
    };
  });
}

export function PositionsTable({ positions, onSelectPosition, onRefreshPosition, onSellTicker }: Props) {
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
  const [refreshingTicker, setRefreshingTicker] = useState<string | null>(null);

  const aggregated = groupPositions(positions);

  const handleRefresh = async (e: React.MouseEvent, agg: AggregatedPosition) => {
    e.stopPropagation();
    setRefreshingTicker(agg.ticker);
    try {
      await onRefreshPosition(agg.ids);
    } finally {
      setRefreshingTicker(null);
    }
  };

  if (aggregated.length === 0) {
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
            <th className="text-right py-3 px-4 font-medium w-28"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {aggregated.map(agg => {
            const isExpanded = expandedTicker === agg.ticker;
            const consensus = agg.latest_consensus;
            const action = consensus?.aggregated_action;
            const dayPositive = (agg.day_change ?? 0) >= 0;
            const pnlPositive = agg.total_pnl >= 0;
            const isMulti = agg.sub_positions.length > 1;
            const primaryId = agg.sub_positions.sort((a, b) => b.quantity - a.quantity)[0].id;

            return (
              <>
                <tr
                  key={agg.ticker}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => setExpandedTicker(isExpanded ? null : agg.ticker)}
                >
                  <td className="py-3 px-4 text-gray-400">
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </td>
                  <td className="py-3 px-4">
                    <button
                      className="font-bold text-gray-900 hover:text-blue-600 transition-colors"
                      onClick={e => { e.stopPropagation(); onSelectPosition(primaryId); }}
                    >
                      {agg.ticker}
                    </button>
                    <div className="text-xs text-gray-400">
                      {agg.quantity.toLocaleString()} shares
                      {isMulti && <span className="ml-1 text-blue-500">· {agg.sub_positions.length} lots</span>}
                    </div>
                    <div className="text-xs text-gray-400">avg {formatCurrency(agg.average_purchase_price)}</div>
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums font-medium text-gray-900">
                    {agg.current_price != null ? formatCurrency(agg.current_price) : '—'}
                  </td>
                  <td className={`py-3 px-4 text-right tabular-nums text-xs ${dayPositive ? 'text-green-600' : 'text-red-600'}`}>
                    {agg.day_change != null ? (
                      <>
                        {dayPositive ? '+' : ''}{agg.day_change.toFixed(2)}<br />
                        <span>({dayPositive ? '+' : ''}{agg.day_change_pct?.toFixed(2)}%)</span>
                      </>
                    ) : '—'}
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums text-gray-600">
                    {agg.portfolio_weight.toFixed(1)}%
                  </td>
                  <td className={`py-3 px-4 text-right tabular-nums ${pnlPositive ? 'text-green-600' : 'text-red-600'}`}>
                    {pnlPositive ? '+' : ''}{formatCurrency(agg.total_pnl)}<br />
                    <span className="text-xs">({pnlPositive ? '+' : ''}{agg.total_pnl_pct.toFixed(2)}%)</span>
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
                          <span
                            key={type}
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
                    <div className="flex items-center justify-end gap-1">
                      <button
                        className="text-gray-400 hover:text-red-500 transition-colors p-1 rounded"
                        onClick={e => { e.stopPropagation(); onSellTicker(agg.ticker, agg.quantity, agg.current_price); }}
                        title="Sell position"
                      >
                        <TrendingDown size={14} />
                      </button>
                      <button
                        className="text-gray-400 hover:text-blue-600 transition-colors p-1 rounded"
                        onClick={e => handleRefresh(e, agg)}
                        title="Refresh recommendations"
                      >
                        {refreshingTicker === agg.ticker ? <InlineSpinner /> : <RefreshCw size={14} />}
                      </button>
                    </div>
                  </td>
                </tr>

                {isExpanded && (
                  <tr key={`expanded-${agg.ticker}`} className="bg-blue-50/50">
                    <td colSpan={9} className="px-8 py-4">
                      {isMulti && (
                        <div className="mb-4">
                          <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Lots</p>
                          <div className="space-y-1">
                            {agg.sub_positions.map(sub => {
                              const subPnl = sub.current_price
                                ? (sub.current_price - sub.average_purchase_price) * sub.quantity
                                : null;
                              return (
                                <div key={sub.id} className="flex items-center gap-4 text-xs text-gray-600 bg-white rounded-lg px-3 py-2 border border-blue-100">
                                  <span className="font-medium text-gray-800 w-32">{sub.purchase_date?.slice(0, 10)}</span>
                                  <span>{sub.quantity.toLocaleString()} sh @ {formatCurrency(sub.average_purchase_price)}</span>
                                  {subPnl != null && (
                                    <span className={subPnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                                      {subPnl >= 0 ? '+' : ''}{formatCurrency(subPnl)}
                                    </span>
                                  )}
                                  <button
                                    className="ml-auto text-xs text-blue-600 hover:underline"
                                    onClick={() => onSelectPosition(sub.id)}
                                  >
                                    Analysis →
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {consensus && (
                        <div>
                          <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Expert Opinions</p>
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
                        </div>
                      )}

                      {!consensus && (
                        <p className="text-xs text-gray-400">No recommendations yet. Click Refresh to generate.</p>
                      )}

                      <div className="mt-3">
                        <button
                          className="text-xs text-blue-600 hover:underline font-medium"
                          onClick={() => onSelectPosition(primaryId)}
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

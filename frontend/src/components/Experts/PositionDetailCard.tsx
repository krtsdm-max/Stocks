import { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw, Edit, TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { getRecommendations, refreshRecommendations, getPositionChart } from '../../services/api';
import type { PositionDetail, ChartData, PortfolioPosition } from '../../types';
import { ActionBadge, ConsensusBadge } from '../Common/Badge';
import { formatCurrency, formatPct } from '../Common/NumberDisplay';
import { LoadingSpinner, InlineSpinner } from '../Common/LoadingSpinner';
import { Card, CardHeader } from '../Common/Card';

const EXPERT_INFO: Record<string, { name: string; color: string; bg: string }> = {
  value: { name: 'Victoria Chen — Value Investor', color: 'text-purple-700', bg: 'bg-purple-50 border-purple-200' },
  momentum: { name: 'Marcus Rivera — Momentum Trader', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
  risk: { name: 'Sophie Nakamura — Risk Manager', color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200' },
};

const CHART_PERIODS = [
  { label: '1W', value: '1w' },
  { label: '1M', value: '1m' },
  { label: '3M', value: '3m' },
  { label: '1Y', value: '1y' },
];

interface Props {
  positionId: number;
  position: PortfolioPosition;
  onBack: () => void;
  onEdit: () => void;
}

export function PositionDetailCard({ positionId, position, onBack, onEdit }: Props) {
  const [detail, setDetail] = useState<PositionDetail | null>(null);
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [chartPeriod, setChartPeriod] = useState('3m');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
  }, [positionId]);

  useEffect(() => {
    loadChart();
  }, [chartPeriod, position.ticker]);

  const loadData = async () => {
    setLoading(true);
    try {
      const d = await getRecommendations(positionId);
      setDetail(d);
    } finally {
      setLoading(false);
    }
  };

  const loadChart = async () => {
    const res = await getPositionChart(position.ticker, chartPeriod);
    setChartData(res.data);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshRecommendations(positionId);
      await loadData();
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) return <LoadingSpinner size="lg" />;

  const consensus = detail?.consensus;
  const pnlPositive = position.total_pnl >= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-2 text-gray-600 hover:text-gray-900 text-sm font-medium">
          <ArrowLeft size={16} /> Back to Portfolio
        </button>
        <div className="flex gap-2">
          <button onClick={onEdit}
            className="flex items-center gap-1 text-sm border border-gray-300 rounded-lg px-3 py-1.5 hover:bg-gray-50">
            <Edit size={14} /> Edit
          </button>
          <button onClick={handleRefresh} disabled={refreshing}
            className="flex items-center gap-1 text-sm bg-blue-600 text-white rounded-lg px-3 py-1.5 hover:bg-blue-700 disabled:opacity-50">
            {refreshing ? <InlineSpinner /> : <RefreshCw size={14} />}
            Refresh Analysis
          </button>
        </div>
      </div>

      {/* Summary Row */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl font-bold text-gray-900">{position.ticker}</h1>
            {detail?.fundamentals?.name && (
              <span className="text-gray-500 text-sm">{detail.fundamentals.name}</span>
            )}
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-600">
            {detail?.fundamentals?.sector && <span className="bg-gray-100 px-2 py-0.5 rounded text-xs">{detail.fundamentals.sector}</span>}
            <span>{position.quantity.toLocaleString()} shares @ {formatCurrency(position.average_purchase_price)}</span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold">{position.current_price != null ? formatCurrency(position.current_price) : '—'}</p>
          {position.day_change != null && (
            <p className={`text-sm ${position.day_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {position.day_change >= 0 ? '+' : ''}{formatCurrency(position.day_change)} ({position.day_change_pct?.toFixed(2)}%)
            </p>
          )}
        </div>
      </div>

      {/* Key metrics row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Value', value: position.total_value != null ? formatCurrency(position.total_value) : '—', icon: <DollarSign size={16} /> },
          {
            label: 'Total P&L', icon: pnlPositive ? <TrendingUp size={16} /> : <TrendingDown size={16} />,
            value: `${pnlPositive ? '+' : ''}${formatCurrency(position.total_pnl)} (${formatPct(position.total_pnl_pct)})`,
            color: pnlPositive ? 'text-green-600' : 'text-red-600',
          },
          { label: 'Weight', value: `${position.portfolio_weight.toFixed(1)}%`, icon: <Activity size={16} /> },
          { label: 'Volatility', value: detail?.technicals?.volatility_annual_pct != null ? `${detail.technicals.volatility_annual_pct.toFixed(1)}% ann.` : '—', icon: <Activity size={16} /> },
        ].map(m => (
          <div key={m.label} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
              {m.icon} {m.label}
            </div>
            <p className={`font-semibold text-sm ${(m as any).color ?? 'text-gray-900'}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Chart */}
      <Card>
        <CardHeader
          title="Price History"
          action={
            <div className="flex gap-1">
              {CHART_PERIODS.map(p => (
                <button
                  key={p.value}
                  onClick={() => setChartPeriod(p.value)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${chartPeriod === p.value ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-gray-100'}`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          }
        />
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 11 }} domain={['auto', 'auto']} tickFormatter={v => `$${v}`} />
              <Tooltip
                formatter={(v: number) => [`$${v.toFixed(2)}`, 'Close']}
                labelFormatter={l => `Date: ${l}`}
              />
              <Line type="monotone" dataKey="close" stroke="#3b82f6" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">No chart data available.</p>
        )}
      </Card>

      {/* Consensus + Expert Votes */}
      <Card>
        <CardHeader title="Expert Committee Verdict" />
        {consensus ? (
          <>
            <div className="flex items-center gap-3 mb-6">
              <ActionBadge action={consensus.aggregated_action} className="text-sm px-4 py-1" />
              <ConsensusBadge level={consensus.consensus_level} />
              <span className="text-xs text-gray-400 ml-auto">
                {new Date(consensus.timestamp).toLocaleString()}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(consensus.expert_votes).map(([type, vote]) => {
                const info = EXPERT_INFO[type];
                return (
                  <div key={type} className={`rounded-xl border p-4 ${info?.bg ?? 'bg-gray-50 border-gray-200'}`}>
                    <div className="flex items-center justify-between mb-3">
                      <span className={`text-xs font-semibold ${info?.color ?? 'text-gray-700'}`}>{info?.name}</span>
                      <ActionBadge action={vote.action} />
                    </div>
                    <p className="text-xs text-gray-700 leading-relaxed">{vote.reasoning}</p>
                    <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                      <span>Confidence: <strong>{vote.confidence_level}%</strong></span>
                      {vote.target_price && <span>Target: <strong>{formatCurrency(vote.target_price)}</strong></span>}
                      {vote.quantity_change && (
                        <span>
                          Qty: <strong>{vote.quantity_change > 0 ? '+' : ''}{vote.quantity_change.toFixed(0)}</strong>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <p className="text-gray-400 text-sm text-center py-6">No recommendations yet. Click "Refresh Analysis" to generate.</p>
        )}
      </Card>

      {/* Technicals + Fundamentals */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {detail?.technicals && (
          <Card>
            <CardHeader title="Technical Indicators" />
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                { label: 'RSI (14)', value: `${detail.technicals.rsi?.toFixed(1)} — ${detail.technicals.rsi_signal}` },
                { label: 'MA 50-day', value: detail.technicals.ma50 != null ? formatCurrency(detail.technicals.ma50) : '—' },
                { label: 'MA 200-day', value: detail.technicals.ma200 != null ? formatCurrency(detail.technicals.ma200) : '—' },
                { label: 'MACD', value: detail.technicals.macd_bullish ? '▲ Bullish' : '▼ Bearish' },
                { label: '3M Momentum', value: detail.technicals.momentum_3m_pct != null ? formatPct(detail.technicals.momentum_3m_pct) : '—' },
                { label: '6M Momentum', value: detail.technicals.momentum_6m_pct != null ? formatPct(detail.technicals.momentum_6m_pct) : '—' },
                { label: '52W High', value: detail.technicals.high_52w != null ? formatCurrency(detail.technicals.high_52w) : '—' },
                { label: '52W Low', value: detail.technicals.low_52w != null ? formatCurrency(detail.technicals.low_52w) : '—' },
              ].map(item => (
                <div key={item.label} className="flex justify-between py-1.5 border-b border-gray-50">
                  <span className="text-gray-500">{item.label}</span>
                  <span className="font-medium text-gray-800">{item.value}</span>
                </div>
              ))}
            </div>
          </Card>
        )}

        {detail?.fundamentals && (
          <Card>
            <CardHeader title="Fundamental Metrics" />
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                { label: 'P/E Ratio', value: detail.fundamentals.pe_ratio?.toFixed(1) ?? '—' },
                { label: 'P/B Ratio', value: detail.fundamentals.pb_ratio?.toFixed(2) ?? '—' },
                { label: 'Div. Yield', value: detail.fundamentals.dividend_yield != null ? `${(detail.fundamentals.dividend_yield * 100).toFixed(2)}%` : '—' },
                { label: 'Beta', value: detail.fundamentals.beta?.toFixed(2) ?? '—' },
                { label: 'Market Cap', value: detail.fundamentals.market_cap != null ? formatCurrency(detail.fundamentals.market_cap / 1e9) + 'B' : '—' },
                { label: 'Sector', value: detail.fundamentals.sector ?? '—' },
              ].map(item => (
                <div key={item.label} className="flex justify-between py-1.5 border-b border-gray-50">
                  <span className="text-gray-500">{item.label}</span>
                  <span className="font-medium text-gray-800">{item.value}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* Recommendation History */}
      {detail?.history && detail.history.length > 0 && (
        <Card>
          <CardHeader title="Recommendation History" subtitle="Track record of past recommendations" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b text-gray-400 uppercase tracking-wider">
                  <th className="text-left py-2 px-3">Date</th>
                  <th className="text-left py-2 px-3">Expert</th>
                  <th className="text-left py-2 px-3">Action</th>
                  <th className="text-right py-2 px-3">At Price</th>
                  <th className="text-right py-2 px-3">Target</th>
                  <th className="text-right py-2 px-3">+1W</th>
                  <th className="text-right py-2 px-3">+1M</th>
                  <th className="text-left py-2 px-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {detail.history.map(r => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="py-2 px-3 text-gray-500">{new Date(r.created_at).toLocaleDateString()}</td>
                    <td className="py-2 px-3 capitalize font-medium text-gray-700">{r.expert_type}</td>
                    <td className="py-2 px-3"><ActionBadge action={r.action} /></td>
                    <td className="py-2 px-3 text-right tabular-nums">{r.snapshot_price ? formatCurrency(r.snapshot_price) : '—'}</td>
                    <td className="py-2 px-3 text-right tabular-nums">{r.target_price ? formatCurrency(r.target_price) : '—'}</td>
                    <td className="py-2 px-3 text-right tabular-nums">{r.actual_price_1w ? formatCurrency(r.actual_price_1w) : '—'}</td>
                    <td className="py-2 px-3 text-right tabular-nums">{r.actual_price_1m ? formatCurrency(r.actual_price_1m) : '—'}</td>
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-1">
                        <div className="h-1.5 rounded-full bg-gray-200 w-20">
                          <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${r.confidence_level}%` }} />
                        </div>
                        <span>{r.confidence_level}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

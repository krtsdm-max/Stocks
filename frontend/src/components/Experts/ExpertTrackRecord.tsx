import { useEffect, useState } from 'react';
import { getExpertTrackRecord } from '../../services/api';
import type { TrackRecord, ExpertType } from '../../types';
import { ActionBadge } from '../Common/Badge';
import { formatCurrency } from '../Common/NumberDisplay';
import { LoadingSpinner } from '../Common/LoadingSpinner';
import { Card, CardHeader } from '../Common/Card';

const EXPERTS: ExpertType[] = ['value', 'momentum', 'risk'];

const EXPERT_DISPLAY: Record<ExpertType, { color: string; bg: string }> = {
  value: { color: 'text-purple-700', bg: 'bg-purple-50 border-purple-200' },
  momentum: { color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
  risk: { color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200' },
};

function StatBox({ label, value, sub }: { label: string; value?: string | number | null; sub?: string }) {
  return (
    <div className="text-center p-3 bg-white rounded-lg border border-gray-100">
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className="font-bold text-gray-900">{value ?? '—'}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export function ExpertTrackRecord() {
  const [records, setRecords] = useState<Record<string, TrackRecord>>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ExpertType>('value');

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const results = await Promise.all(EXPERTS.map(e => getExpertTrackRecord(e)));
      const map: Record<string, TrackRecord> = {};
      results.forEach(r => { map[r.expert_type] = r; });
      setRecords(map);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  const active = records[activeTab];
  const display = EXPERT_DISPLAY[activeTab];

  return (
    <div className="space-y-6">
      {/* Tab selector */}
      <div className="flex gap-2">
        {EXPERTS.map(type => {
          const r = records[type];
          const d = EXPERT_DISPLAY[type];
          return (
            <button
              key={type}
              onClick={() => setActiveTab(type)}
              className={`flex-1 p-4 rounded-xl border text-left transition-all ${activeTab === type ? d.bg + ' border-opacity-100' : 'bg-white border-gray-200 hover:border-gray-300'}`}
            >
              <p className={`font-semibold text-sm ${activeTab === type ? d.color : 'text-gray-700'}`}>
                {r?.expert_name}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{r?.expert_title}</p>
              {r?.track_record.direction_accuracy_pct != null && (
                <p className={`text-xs font-bold mt-1 ${activeTab === type ? d.color : 'text-gray-400'}`}>
                  {r.track_record.direction_accuracy_pct}% accuracy
                </p>
              )}
            </button>
          );
        })}
      </div>

      {active && (
        <>
          <Card>
            <CardHeader title={`${active.expert_name} — ${active.expert_title}`} />
            <p className="text-sm text-gray-600 italic border-l-4 border-gray-200 pl-3 mb-5">
              "{active.philosophy}"
            </p>

            {/* Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatBox
                label="Total Recs"
                value={active.track_record.total_recommendations}
              />
              <StatBox
                label="Direction Accuracy"
                value={active.track_record.direction_accuracy_pct != null
                  ? `${active.track_record.direction_accuracy_pct}%`
                  : null}
                sub={`${active.track_record.evaluated_1w} evaluated`}
              />
              <StatBox
                label="Avg Price Error (1W)"
                value={active.track_record.avg_price_error_1w_pct != null
                  ? `${active.track_record.avg_price_error_1w_pct}%`
                  : null}
              />
              <StatBox
                label="Avg Price Error (1M)"
                value={active.track_record.avg_price_error_1m_pct != null
                  ? `${active.track_record.avg_price_error_1m_pct}%`
                  : null}
              />
            </div>

            {/* Action distribution */}
            {Object.keys(active.action_distribution).length > 0 && (
              <div className="mt-5">
                <p className="text-sm font-medium text-gray-700 mb-3">Action Distribution</p>
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(active.action_distribution)
                    .sort((a, b) => b[1] - a[1])
                    .map(([action, count]) => (
                      <div key={action} className="flex items-center gap-1.5">
                        <ActionBadge action={action as any} />
                        <span className="text-xs text-gray-500">×{count}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </Card>

          {/* Recent recommendations */}
          {active.recent_recommendations.length > 0 && (
            <Card>
              <CardHeader title="Recent Recommendations" />
              <div className="space-y-3">
                {active.recent_recommendations.map(rec => (
                  <div key={rec.id} className="flex items-start gap-3 py-3 border-b border-gray-50 last:border-0">
                    <ActionBadge action={rec.action} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-sm text-gray-900">{rec.ticker}</span>
                        {rec.target_price && (
                          <span className="text-xs text-gray-500">Target: {formatCurrency(rec.target_price)}</span>
                        )}
                        <span className="text-xs text-gray-400 ml-auto">{new Date(rec.created_at).toLocaleDateString()}</span>
                      </div>
                      <p className="text-xs text-gray-600 line-clamp-2">{rec.reasoning}</p>
                      {(rec.actual_price_1w || rec.actual_price_1m) && (
                        <div className="flex gap-3 mt-1.5 text-xs text-gray-400">
                          {rec.actual_price_1w && <span>1W actual: {formatCurrency(rec.actual_price_1w)}</span>}
                          {rec.actual_price_1m && <span>1M actual: {formatCurrency(rec.actual_price_1m)}</span>}
                        </div>
                      )}
                    </div>
                    <div className="text-xs text-gray-400">
                      <div className="h-1.5 w-16 bg-gray-200 rounded-full">
                        <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${rec.confidence_level}%` }} />
                      </div>
                      <span>{rec.confidence_level}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

import { useState } from 'react';
import { Shield, RefreshCw } from 'lucide-react';
import { updateSettings, refreshAllRecommendations } from '../../services/api';
import type { UserSettings, RiskProfile } from '../../types';
import { InlineSpinner } from '../Common/LoadingSpinner';
import { Card, CardHeader } from '../Common/Card';

const PROFILES: { value: RiskProfile; label: string; description: string; color: string }[] = [
  {
    value: 'conservative',
    label: 'Conservative',
    description: 'Max 5% per position, 15% per sector. Low volatility tolerance.',
    color: 'border-blue-400 bg-blue-50',
  },
  {
    value: 'balanced',
    label: 'Balanced',
    description: 'Max 10% per position, 25% per sector. Medium volatility tolerance.',
    color: 'border-yellow-400 bg-yellow-50',
  },
  {
    value: 'aggressive',
    label: 'Aggressive',
    description: 'Max 15% per position, 35% per sector. High volatility tolerance.',
    color: 'border-red-400 bg-red-50',
  },
];

interface Props {
  settings: UserSettings;
  onUpdated: () => void;
}

export function SettingsPanel({ settings, onUpdated }: Props) {
  const [saving, setSaving] = useState(false);
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [message, setMessage] = useState('');

  const handleSelectProfile = async (profile: RiskProfile) => {
    if (profile === settings.risk_profile) return;
    setSaving(true);
    setMessage('');
    try {
      await updateSettings({ risk_profile: profile });
      setMessage('Risk profile updated. Refreshing recommendations...');
      onUpdated();
    } finally {
      setSaving(false);
    }
  };

  const handleRefreshAll = async () => {
    setRefreshingAll(true);
    setMessage('');
    try {
      const result = await refreshAllRecommendations() as any;
      setMessage(`Updated recommendations for ${result.updated}/${result.total} positions.`);
    } finally {
      setRefreshingAll(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader
          title="Risk Profile"
          subtitle="Affects concentration limits and thresholds for all three experts."
        />

        <div className="space-y-3">
          {PROFILES.map(p => (
            <button
              key={p.value}
              onClick={() => handleSelectProfile(p.value)}
              disabled={saving}
              className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                settings.risk_profile === p.value ? p.color + ' ring-2 ring-offset-1 ring-blue-400' : 'border-gray-200 hover:border-gray-300 bg-white'
              } disabled:opacity-60`}
            >
              <div className="flex items-center gap-2">
                <Shield size={16} className={settings.risk_profile === p.value ? 'text-blue-600' : 'text-gray-400'} />
                <span className="font-semibold text-gray-900">{p.label}</span>
                {settings.risk_profile === p.value && (
                  <span className="ml-auto text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">Active</span>
                )}
              </div>
              <p className="text-sm text-gray-500 mt-1">{p.description}</p>
            </button>
          ))}
        </div>

        {message && (
          <p className="text-sm text-green-600 mt-3 bg-green-50 rounded-lg p-3">{message}</p>
        )}
      </Card>

      <Card>
        <CardHeader title="Recommendation Engine" subtitle="Manually trigger recommendation refresh for all positions." />
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefreshAll}
            disabled={refreshingAll}
            className="flex items-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {refreshingAll ? <InlineSpinner /> : <RefreshCw size={16} />}
            Refresh All Recommendations
          </button>
          <p className="text-xs text-gray-400">Normally runs hourly during NYSE trading hours (9:30–16:00 EST)</p>
        </div>
      </Card>

      <Card>
        <CardHeader title="Current Limits" />
        <div className="grid grid-cols-3 gap-4 text-sm">
          {[
            { label: 'Max Position', value: `${settings.max_position_concentration}%` },
            { label: 'Max Sector', value: `${settings.sector_concentration_limit}%` },
            { label: 'Volatility Target', value: settings.target_volatility },
          ].map(item => (
            <div key={item.label} className="text-center bg-gray-50 rounded-lg p-3">
              <p className="text-gray-400 text-xs mb-1">{item.label}</p>
              <p className="font-bold text-gray-900 text-lg capitalize">{item.value}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { getSettings } from '../services/api';
import type { UserSettings } from '../types';
import { SettingsPanel } from '../components/Dashboard/SettingsPanel';
import { LoadingSpinner } from '../components/Common/LoadingSpinner';

export function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const s = await getSettings();
      setSettings(s);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <LoadingSpinner />;
  if (!settings) return null;

  return (
    <div>
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-500">Configure your risk profile and recommendation engine.</p>
      </div>
      <SettingsPanel settings={settings} onUpdated={load} />
    </div>
  );
}

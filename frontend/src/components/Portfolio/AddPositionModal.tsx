import { useState } from 'react';
import { X, AlertCircle, CheckCircle } from 'lucide-react';
import { createPosition, validateTicker } from '../../services/api';
import { InlineSpinner } from '../Common/LoadingSpinner';

interface Props {
  onClose: () => void;
  onAdded: () => void;
}

export function AddPositionModal({ onClose, onAdded }: Props) {
  const [form, setForm] = useState({
    ticker: '',
    quantity: '',
    average_purchase_price: '',
    purchase_date: new Date().toISOString().split('T')[0],
    notes: '',
  });
  const [validating, setValidating] = useState(false);
  const [tickerValid, setTickerValid] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleTickerBlur = async () => {
    if (!form.ticker) return;
    setValidating(true);
    setTickerValid(null);
    try {
      const res = await validateTicker(form.ticker);
      setTickerValid(res.valid);
      // Show a warning but don't set error — user can still submit
      if (!res.valid) setError(`Warning: "${form.ticker}" was not confirmed on Yahoo Finance. You can still add it manually.`);
      else setError('');
    } catch {
      // Network error — don't penalise the user, treat as unknown
      setTickerValid(null);
      setError('');
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!tickerValid) {
      setError('Please enter a valid ticker.');
      return;
    }
    setSaving(true);
    try {
      await createPosition({
        ticker: form.ticker.toUpperCase(),
        quantity: parseFloat(form.quantity),
        average_purchase_price: parseFloat(form.average_purchase_price),
        purchase_date: form.purchase_date,
        notes: form.notes || undefined,
      });
      onAdded();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to add position.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Add Position</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className={`flex items-center gap-2 rounded-lg p-3 text-sm ${
              error.startsWith('Warning:')
                ? 'text-amber-700 bg-amber-50'
                : 'text-red-600 bg-red-50'
            }`}>
              <AlertCircle size={16} className="flex-none" />
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ticker Symbol *</label>
            <div className="relative">
              <input
                type="text"
                value={form.ticker}
                onChange={e => { setForm(f => ({ ...f, ticker: e.target.value.toUpperCase() })); setTickerValid(null); }}
                onBlur={handleTickerBlur}
                placeholder="e.g. AAPL"
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-8"
              />
              <span className="absolute right-2 top-1/2 -translate-y-1/2">
                {validating && <InlineSpinner />}
                {!validating && tickerValid === true && <CheckCircle size={16} className="text-green-500" />}
                {!validating && tickerValid === false && <AlertCircle size={16} className="text-red-500" />}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quantity *</label>
              <input
                type="number"
                value={form.quantity}
                onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
                min="0.000001"
                step="any"
                placeholder="100"
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Avg. Buy Price *</label>
              <input
                type="number"
                value={form.average_purchase_price}
                onChange={e => setForm(f => ({ ...f, average_purchase_price: e.target.value }))}
                min="0.0001"
                step="any"
                placeholder="150.00"
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Purchase Date *</label>
            <input
              type="date"
              value={form.purchase_date}
              onChange={e => setForm(f => ({ ...f, purchase_date: e.target.value }))}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              rows={2}
              placeholder="Reason for entry, thesis..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm font-medium hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={saving || validating}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
              {saving ? <><InlineSpinner /> Adding...</> : 'Add Position'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

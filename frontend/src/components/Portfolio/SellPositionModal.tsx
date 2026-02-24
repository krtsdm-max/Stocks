import { useState } from 'react';
import { X, AlertCircle, TrendingDown } from 'lucide-react';
import { sellPosition } from '../../services/api';
import { InlineSpinner } from '../Common/LoadingSpinner';
import { formatCurrency } from '../Common/NumberDisplay';

interface Props {
  ticker: string;
  totalQuantity: number;
  currentPrice?: number;
  onClose: () => void;
  onSold: () => void;
}

export function SellPositionModal({ ticker, totalQuantity, currentPrice, onClose, onSold }: Props) {
  const [quantity, setQuantity] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const qty = parseFloat(quantity) || 0;
  const proceeds = currentPrice && qty > 0 ? qty * currentPrice : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!qty || qty <= 0) { setError('Enter a valid quantity'); return; }
    if (qty > totalQuantity + 1e-9) {
      setError(`Only ${totalQuantity.toLocaleString()} shares available`);
      return;
    }
    setSubmitting(true);
    try {
      await sellPosition(ticker, qty);
      onSold();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to sell position.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm">
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-2">
            <TrendingDown size={18} className="text-red-500" />
            <h2 className="text-lg font-semibold text-gray-900">Sell {ticker}</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 text-red-600 bg-red-50 rounded-lg p-3 text-sm">
              <AlertCircle size={16} className="flex-none" /> {error}
            </div>
          )}

          <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600 space-y-1">
            <div className="flex justify-between">
              <span>Available shares</span>
              <span className="font-medium text-gray-900">{totalQuantity.toLocaleString()}</span>
            </div>
            {currentPrice && (
              <div className="flex justify-between">
                <span>Current price</span>
                <span className="font-medium text-gray-900">{formatCurrency(currentPrice)}</span>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Shares to Sell *</label>
            <input
              type="number"
              value={quantity}
              onChange={e => setQuantity(e.target.value)}
              min="0.000001"
              max={totalQuantity}
              step="any"
              placeholder={totalQuantity.toString()}
              required
              autoFocus
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
            />
            <button
              type="button"
              onClick={() => setQuantity(totalQuantity.toString())}
              className="mt-1 text-xs text-blue-600 hover:underline"
            >
              Sell all
            </button>
          </div>

          {proceeds != null && (
            <div className="flex justify-between text-sm border-t pt-3">
              <span className="text-gray-500">Estimated proceeds</span>
              <span className="font-semibold text-gray-900">{formatCurrency(proceeds)}</span>
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm font-medium hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !qty || qty <= 0}
              className="flex-1 bg-red-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting ? <><InlineSpinner /> Selling...</> : 'Confirm Sell'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

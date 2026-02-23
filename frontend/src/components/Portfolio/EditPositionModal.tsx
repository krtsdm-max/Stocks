import { useState } from 'react';
import { X, AlertCircle, Trash2 } from 'lucide-react';
import { updatePosition, deletePosition } from '../../services/api';
import type { PortfolioPosition } from '../../types';
import { InlineSpinner } from '../Common/LoadingSpinner';

interface Props {
  position: PortfolioPosition;
  onClose: () => void;
  onUpdated: () => void;
  onDeleted: () => void;
}

export function EditPositionModal({ position, onClose, onUpdated, onDeleted }: Props) {
  const [form, setForm] = useState({
    quantity: String(position.quantity),
    average_purchase_price: String(position.average_purchase_price),
    purchase_date: position.purchase_date,
    notes: position.notes ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await updatePosition(position.id, {
        quantity: parseFloat(form.quantity),
        average_purchase_price: parseFloat(form.average_purchase_price),
        purchase_date: form.purchase_date,
        notes: form.notes || undefined,
      });
      onUpdated();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Update failed.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deletePosition(position.id);
      onDeleted();
      onClose();
    } catch {
      setError('Failed to delete position.');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Edit {position.ticker}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 text-red-600 bg-red-50 rounded-lg p-3 text-sm">
              <AlertCircle size={16} /> {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quantity *</label>
              <input
                type="number" value={form.quantity}
                onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
                min="0.000001" step="any" required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Avg. Buy Price *</label>
              <input
                type="number" value={form.average_purchase_price}
                onChange={e => setForm(f => ({ ...f, average_purchase_price: e.target.value }))}
                min="0.0001" step="any" required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Purchase Date *</label>
            <input
              type="date" value={form.purchase_date}
              onChange={e => setForm(f => ({ ...f, purchase_date: e.target.value }))}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm font-medium hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
              {saving ? <><InlineSpinner /> Saving...</> : 'Save Changes'}
            </button>
          </div>
        </form>

        <div className="px-6 pb-6 pt-0">
          {!confirmDelete ? (
            <button
              onClick={() => setConfirmDelete(true)}
              className="w-full flex items-center justify-center gap-2 text-red-600 border border-red-200 rounded-lg py-2 text-sm hover:bg-red-50 transition-colors"
            >
              <Trash2 size={14} /> Delete Position
            </button>
          ) : (
            <div className="border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700 mb-3">Delete {position.ticker}? This cannot be undone.</p>
              <div className="flex gap-2">
                <button onClick={() => setConfirmDelete(false)}
                  className="flex-1 border border-gray-300 rounded-lg py-1.5 text-xs text-gray-600 hover:bg-gray-50">
                  Cancel
                </button>
                <button onClick={handleDelete} disabled={deleting}
                  className="flex-1 bg-red-600 text-white rounded-lg py-1.5 text-xs hover:bg-red-700 disabled:opacity-50 flex items-center justify-center gap-1">
                  {deleting ? <InlineSpinner /> : <Trash2 size={12} />} Confirm Delete
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

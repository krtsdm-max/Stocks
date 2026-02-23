import clsx from 'clsx';
import type { Action, ConsensusLevel } from '../../types';

const ACTION_STYLES: Record<string, string> = {
  buy: 'bg-green-100 text-green-800 border border-green-200',
  add: 'bg-emerald-100 text-emerald-800 border border-emerald-200',
  hold: 'bg-blue-100 text-blue-800 border border-blue-200',
  reduce: 'bg-orange-100 text-orange-800 border border-orange-200',
  sell: 'bg-red-100 text-red-800 border border-red-200',
  close: 'bg-red-900 text-red-100 border border-red-700',
};

const CONSENSUS_STYLES: Record<string, string> = {
  unanimous: 'bg-green-50 text-green-700 border border-green-200',
  majority: 'bg-yellow-50 text-yellow-700 border border-yellow-200',
  split: 'bg-red-50 text-red-700 border border-red-200',
};

interface ActionBadgeProps {
  action: Action;
  className?: string;
}

export function ActionBadge({ action, className }: ActionBadgeProps) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide',
      ACTION_STYLES[action] ?? 'bg-gray-100 text-gray-800',
      className,
    )}>
      {action}
    </span>
  );
}

interface ConsensusBadgeProps {
  level: ConsensusLevel;
  className?: string;
}

export function ConsensusBadge({ level, className }: ConsensusBadgeProps) {
  const labels: Record<string, string> = {
    unanimous: '3/3 Unanimous',
    majority: '2/3 Majority',
    split: '1/3 Split',
  };
  return (
    <span className={clsx(
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
      CONSENSUS_STYLES[level] ?? 'bg-gray-100 text-gray-700',
      className,
    )}>
      {labels[level] ?? level}
    </span>
  );
}

import clsx from 'clsx';

interface PnlProps {
  value: number;
  pct?: number;
  className?: string;
  showSign?: boolean;
}

export function PnlDisplay({ value, pct, className, showSign = true }: PnlProps) {
  const positive = value >= 0;
  return (
    <span className={clsx(
      'font-medium tabular-nums',
      positive ? 'text-green-600' : 'text-red-600',
      className,
    )}>
      {showSign && (positive ? '+' : '')}
      {formatCurrency(value)}
      {pct !== undefined && (
        <span className="ml-1 text-sm">({showSign && positive ? '+' : ''}{pct.toFixed(2)}%)</span>
      )}
    </span>
  );
}

export function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${value.toFixed(2)}`;
}

export function formatPct(value: number, showSign = true): string {
  const sign = showSign && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatNumber(value: number, decimals = 2): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

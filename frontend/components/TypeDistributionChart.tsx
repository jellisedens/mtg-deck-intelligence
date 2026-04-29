"use client";

interface Props {
  typeDistribution: Record<string, number> | { type: string; count: number }[];
  totalCards: number;
}

export default function TypeDistributionChart({ typeDistribution, totalCards }: Props) {
  // Normalize to array format
  const entries = Array.isArray(typeDistribution)
    ? typeDistribution
    : Object.entries(typeDistribution).map(([type, count]) => ({
        type,
        count: Number(count),
      }));

  const sorted = [...entries]
    .filter((t) => t.count > 0)
    .sort((a, b) => b.count - a.count);

  if (sorted.length === 0) return null;

  const maxCount = sorted[0]?.count || 1;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xxs text-text-muted uppercase tracking-wider">
          Card Types
        </span>
        <span className="text-xxs text-text-secondary">
          {totalCards} total
        </span>
      </div>
      <div className="space-y-1.5">
        {sorted.map((t) => {
          const pct = (t.count / maxCount) * 100;
          return (
            <div key={t.type} className="flex items-center gap-2">
              <span className="text-xs text-text-secondary w-24 text-right truncate">
                {t.type}
              </span>
              <div className="flex-1 h-3 bg-bg-primary rounded overflow-hidden">
                <div
                  className="h-full bg-accent-green/40 rounded"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs text-text-primary w-6 text-right">
                {t.count}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
"use client";

const COLOR_MAP: Record<string, { label: string; fill: string }> = {
  W: { label: "White", fill: "#f9f4e8" },
  U: { label: "Blue", fill: "#0e68ab" },
  B: { label: "Black", fill: "#3d3329" },
  R: { label: "Red", fill: "#d3202a" },
  G: { label: "Green", fill: "#00733e" },
};

interface ColorHealth {
  score: number;
  sim_access: number;
  sources: number;
  pips: number;
  adequacy: number;
}

interface Props {
  colorHealth: Record<string, ColorHealth>;
  fixPriority: string[];
  overallHealth: number;
}

function getScoreColor(score: number): string {
  if (score >= 85) return "text-accent-green";
  if (score >= 70) return "text-accent-yellow";
  return "text-accent-red";
}

export default function ColorHealthChart({ colorHealth, fixPriority, overallHealth }: Props) {
  const colors = ["W", "U", "B", "R", "G"];

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xxs text-text-muted uppercase tracking-wider">
          Color Health
        </span>
        <span className={`text-xs font-medium ${getScoreColor(overallHealth)}`}>
          {overallHealth.toFixed(0)}%
        </span>
      </div>

      <div className="space-y-2">
        {colors.map((c) => {
          const health = colorHealth[c];
          if (!health) return null;

          const info = COLOR_MAP[c];
          const score = health.score;

          return (
            <div key={c}>
              <div className="flex items-center justify-between mb-0.5">
                <div className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ background: info.fill }}
                  />
                  <span className="text-xs text-text-secondary">{info.label}</span>
                </div>
                <span className={`text-xs font-medium ${getScoreColor(score)}`}>
                  {score.toFixed(0)}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-bg-primary rounded overflow-hidden">
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${score}%`,
                      background: info.fill,
                      opacity: 0.7,
                    }}
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-0.5">
                <span className="text-xxs text-text-muted">
                  {health.sources} sources
                </span>
                <span className="text-xxs text-text-muted">
                  {health.pips} pips
                </span>
                <span className="text-xxs text-text-muted">
                  {health.sim_access.toFixed(0)}% access
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {fixPriority.length > 0 && (
        <div className="mt-3 pt-2 border-t border-border">
          <span className="text-xxs text-text-muted">fix priority: </span>
          <span className="text-xxs text-text-secondary">
            {fixPriority.map((c) => COLOR_MAP[c]?.label || c).join(" → ")}
          </span>
        </div>
      )}
    </div>
  );
}
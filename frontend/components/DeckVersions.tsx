"use client";

import { useState, useEffect } from "react";

interface Version {
  id: string;
  version_number: number;
  name: string | null;
  card_count: number;
  created_at: string;
  analytics_snapshot: AnalyticsData | null;
  strategy_snapshot: Record<string, unknown> | null;
}

interface AnalyticsData {
  total_cards?: number;
  average_cmc?: number;
  mana_curve?: Record<string, number>;
  type_distribution?: Record<string, number>;
  color_distribution?: Record<string, { name: string; count: number }>;
  mana_base?: Record<string, unknown>;
  simulation?: {
    games_simulated: number;
    mana_on_curve_pct?: Record<string, number>;
    avg_lands_by_turn?: Record<string, number>;
  };
  color_health?: Record<string, { score: number; status: string }>;
}

interface DeckStats {
  label: string;
  versionId?: string;
  versionNumber?: number;
  name?: string | null;
  cardCount: number;
  averageCmc: number | null;
  landCount: number | null;
  rampCount: number | null;
  drawCount: number | null;
  removalCount: number | null;
  creatureCount: number | null;
  simGames: number;
  colorHealth: Record<string, { score: number; status: string }> | null;
  createdAt?: string;
  cardSnapshot?: Array<{ card_name: string; quantity: number; board: string }>;
}

interface Props {
  deckId: string;
  cardCount: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

function getToken() {
  return localStorage.getItem("mtg_token") || "";
}

function StatRow({
  label,
  current,
  version,
  higherIsBetter = true,
}: {
  label: string;
  current: number | null;
  version: number | null;
  higherIsBetter?: boolean;
}) {
  if (current == null && version == null) return null;

  let indicator = "";
  let indicatorClass = "text-text-muted";
  if (current != null && version != null && current !== version) {
    const diff = version - current;
    const better = higherIsBetter ? diff > 0 : diff < 0;
    indicator = better ? " ▲" : " ▼";
    indicatorClass = better ? "text-accent-green" : "text-accent-red";
  }

  return (
    <div className="flex justify-between text-xxs">
      <span className="text-text-muted">{label}</span>
      <span className="text-text-secondary">
        {version != null ? version : "—"}
        <span className={indicatorClass}>{indicator}</span>
      </span>
    </div>
  );
}

function StatsCard({
  stats,
  isCurrent,
  currentStats,
  onCompare,
  onRestore,
  onDelete,
  restoring,
  diffData,
}: {
  stats: DeckStats;
  isCurrent: boolean;
  currentStats: DeckStats | null;
  onCompare?: () => void;
  onRestore?: () => void;
  onDelete?: () => void;
  restoring?: boolean;
  diffData: DiffData | null;
}) {
  const [showDiff, setShowDiff] = useState(false);

  return (
    <div
      className={`border rounded p-3 min-w-[200px] space-y-2 ${
        isCurrent
          ? "border-accent-green/40 bg-accent-green/5"
          : "border-border"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs text-text-primary font-medium">
            {isCurrent ? `v${stats.versionNumber} (latest)` : `v${stats.versionNumber}`}
          </span>
          {stats.name && (
            <span className="text-xxs text-text-muted ml-1">— {stats.name}</span>
          )}
        </div>
        <span className="text-xxs text-text-muted">{stats.cardCount} cards</span>
      </div>

      {stats.createdAt && (
        <div className="text-xxs text-text-muted">
          {new Date(stats.createdAt).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
          })}
        </div>
      )}

      {/* Stats */}
      <div className="space-y-0.5">
        <StatRow
          label="avg CMC"
          current={currentStats?.averageCmc ?? null}
          version={stats.averageCmc}
          higherIsBetter={false}
        />
        <StatRow
          label="lands"
          current={currentStats?.landCount ?? null}
          version={stats.landCount}
          higherIsBetter={true}
        />
        <StatRow
          label="ramp"
          current={currentStats?.rampCount ?? null}
          version={stats.rampCount}
          higherIsBetter={true}
        />
        <StatRow
          label="draw"
          current={currentStats?.drawCount ?? null}
          version={stats.drawCount}
          higherIsBetter={true}
        />
        <StatRow
          label="removal"
          current={currentStats?.removalCount ?? null}
          version={stats.removalCount}
          higherIsBetter={true}
        />
        <StatRow
          label="creatures"
          current={currentStats?.creatureCount ?? null}
          version={stats.creatureCount}
          higherIsBetter={true}
        />
        {stats.simGames > 0 && (
          <div className="text-xxs text-text-muted mt-1">
            {stats.simGames} games simulated
          </div>
        )}
      </div>

      {/* Color health */}
      {stats.colorHealth && (
        <div className="space-y-0.5">
          <span className="text-xxs text-text-muted">color health</span>
          {Object.entries(stats.colorHealth).map(([color, data]) => {
            const currentScore = !isCurrent && currentStats?.colorHealth
              ? currentStats.colorHealth[color]?.score ?? null
              : null;
            const diff = currentScore != null && data.score !== currentScore
              ? data.score - currentScore
              : null;
            return (
              <div key={color} className="flex justify-between text-xxs">
                <span className="text-text-muted">{color}</span>
                <span>
                  <span className={
                    data.score >= 80 ? "text-accent-green" : data.score >= 65 ? "text-accent-yellow" : "text-accent-red"
                  }>
                    {data.score}
                  </span>
                  {diff != null && (
                    <span className={diff > 0 ? "text-accent-green" : "text-accent-red"}>
                      {diff > 0 ? " ▲" : " ▼"}
                    </span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Actions */}
      {!isCurrent && (
        <div className="flex gap-1 pt-1 border-t border-border">
          <button
            onClick={() => {
              if (onCompare) onCompare();
              setShowDiff(!showDiff);
            }}
            className={`text-xxs px-2 py-0.5 rounded transition-colors ${
              showDiff
                ? "bg-accent-green/20 text-accent-green"
                : "bg-bg-tertiary text-text-muted hover:text-text-secondary"
            }`}
          >
            {showDiff ? "hide diff" : "diff"}
          </button>
          <button
            onClick={onRestore}
            disabled={restoring}
            className="text-xxs px-2 py-0.5 rounded bg-bg-tertiary text-text-muted hover:text-accent-yellow transition-colors"
          >
            {restoring ? "..." : "restore"}
          </button>
          <button
            onClick={onDelete}
            className="text-xxs px-2 py-0.5 rounded bg-bg-tertiary text-text-muted hover:text-accent-red transition-colors ml-auto"
          >
            ✕
          </button>
        </div>
      )}

      {/* Diff details */}
      {showDiff && diffData && (
        <div className="pt-2 border-t border-border space-y-1">
          {diffData.added.length > 0 && (
            <div>
              <span className="text-xxs text-accent-green">+ {diffData.added.length} added since</span>
              <div className="ml-2">
                {diffData.added.map((c, i) => (
                  <div key={i} className="text-xxs text-text-muted">{c.card_name}</div>
                ))}
              </div>
            </div>
          )}
          {diffData.removed.length > 0 && (
            <div>
              <span className="text-xxs text-accent-red">− {diffData.removed.length} removed since</span>
              <div className="ml-2">
                {diffData.removed.map((c, i) => (
                  <div key={i} className="text-xxs text-text-muted">{c.card_name}</div>
                ))}
              </div>
            </div>
          )}
          {diffData.added.length === 0 && diffData.removed.length === 0 && (
            <p className="text-xxs text-text-muted">no changes</p>
          )}
        </div>
      )}
    </div>
  );
}

interface DiffData {
  added: Array<{ card_name: string }>;
  removed: Array<{ card_name: string }>;
  changed: Array<{ card_name: string }>;
}

export default function DeckVersions({ deckId, cardCount }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [versions, setVersions] = useState<Version[]>([]);
  const [currentStats, setCurrentStats] = useState<DeckStats | null>(null);
  const [versionStats, setVersionStats] = useState<DeckStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [snapshotName, setSnapshotName] = useState("");
  const [showNameInput, setShowNameInput] = useState(false);
  const [diffs, setDiffs] = useState<Record<string, DiffData>>({});


  function _parseColorHealth(raw: Record<string, unknown>, colorIdentity?: string): Record<string, { score: number; status: string }> | null {
    const perColor = (raw.color_health || raw) as Record<string, { score: number; sources?: number; pips?: number }>;
    if (!perColor || typeof perColor !== "object") return null;

    const deckColors = colorIdentity ? colorIdentity.split("") : null;
    const result: Record<string, { score: number; status: string }> = {};

    // Add overall health
    if (raw.overall_health != null) {
      const score = Number(raw.overall_health);
      result["overall"] = {
        score: Math.round(score),
        status: score >= 80 ? "healthy" : score >= 65 ? "fair" : "critical",
      };
    }

    // Add per-color health — filter by color identity AND by actual usage
    for (const [color, data] of Object.entries(perColor)) {
      if (!data || typeof data !== "object" || !("score" in data)) continue;
      // Skip colors not in deck identity
      if (deckColors && !deckColors.includes(color)) continue;
      // Skip colors with no pips and no sources (not used in deck)
      if ((data.pips || 0) === 0 && (data.sources || 0) === 0) continue;
      result[color] = {
        score: Math.round(data.score),
        status: data.score >= 80 ? "healthy" : data.score >= 65 ? "fair" : "critical",
      };
    }

    return Object.keys(result).length > 0 ? result : null;
  }

  async function loadData() {
    setLoading(true);
    try {
      // Fetch versions list
      const versRes = await fetch(`${API_BASE}/decks/${deckId}/versions`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!versRes.ok) return;
      
      const versList = await versRes.json();
      setVersions(versList);

      // Fetch full details for each version
      const statsPromises = versList.map(async (v: Version) => {
        const detailRes = await fetch(`${API_BASE}/decks/${deckId}/versions/${v.id}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        });
        if (detailRes.ok) {
          const detail = await detailRes.json();
          const analytics = detail.analytics_snapshot || {};
          const sim = analytics.simulation || {};
          const strat = detail.strategy_snapshot || {};
          const roleDist = strat.role_distribution || {};
          return {
            label: `v${v.version_number}`,
            versionId: v.id,
            versionNumber: v.version_number,
            name: v.name,
            cardCount: v.card_count,
            averageCmc: analytics.average_cmc || null,
            landCount: analytics.type_distribution?.Land || roleDist.land || null,
            rampCount: roleDist.ramp || null,
            drawCount: roleDist.card_draw || null,
            removalCount: ((roleDist.removal || 0) + (roleDist.board_wipe || 0)) || null,
            creatureCount: analytics.type_distribution?.Creature || roleDist.creature || null,
            simGames: sim.games_simulated || 0,
            colorHealth: analytics.color_health ? _parseColorHealth(analytics.color_health, strat.color_identity) : null,
            createdAt: v.created_at,
          } as DeckStats;
        }
        return null;
      });
      const resolved = await Promise.all(statsPromises);
      const allStats = resolved.filter(Boolean) as DeckStats[];
      setVersionStats(allStats);

      // Use the latest version as the baseline for comparison
      if (allStats.length > 0) {
        setCurrentStats(allStats[0]); // versions are sorted desc, so [0] is latest
      } else {
        setCurrentStats(null);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (expanded) {
      loadData();
    }
  }, [expanded]);

  async function handleCreate() {
    setCreating(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/decks/${deckId}/versions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: snapshotName || null }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Failed to create snapshot");
      }
      setSnapshotName("");
      setShowNameInput(false);
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create snapshot");
    } finally {
      setCreating(false);
    }
  }

  async function handleRestore(versionId: string, versionNumber: number) {
    if (!confirm(`Restore to version ${versionNumber}? Current state will be auto-saved first.`)) {
      return;
    }
    setRestoring(versionId);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/decks/${deckId}/versions/${versionId}/restore`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Content-Type": "application/json",
        },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Failed to restore");
      }
      window.location.reload();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to restore");
    } finally {
      setRestoring(null);
    }
  }

  async function handleDelete(versionId: string, versionNumber: number) {
    if (!confirm(`Delete version ${versionNumber}? This cannot be undone.`)) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/decks/${deckId}/versions/${versionId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Failed to delete");
      }
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  async function handleDiff(versionId: string) {
    if (diffs[versionId]) {
      const newDiffs = { ...diffs };
      delete newDiffs[versionId];
      setDiffs(newDiffs);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/decks/${deckId}/versions/${versionId}/diff`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDiffs({ ...diffs, [versionId]: data });
      }
    } catch {
      // silent
    }
  }

  return (
    <div className="panel">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-bg-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted font-medium uppercase tracking-wider">
            Versions
          </span>
          {versions.length > 0 && !expanded && (
            <span className="text-xxs text-text-muted">{versions.length}</span>
          )}
        </div>
        <span className="text-text-muted text-xs">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Create snapshot */}
          {!showNameInput ? (
            <button
              onClick={() => setShowNameInput(true)}
              className="btn-primary text-xs w-full"
            >
              create snapshot
            </button>
          ) : (
            <div className="space-y-1">
              <input
                type="text"
                value={snapshotName}
                onChange={(e) => setSnapshotName(e.target.value)}
                className="input-terminal text-xs w-full"
                placeholder="snapshot name (optional)"
                autoFocus
              />
              <div className="flex gap-1">
                <button
                  onClick={handleCreate}
                  disabled={creating}
                  className="btn-primary text-xs flex-1"
                >
                  {creating ? "saving..." : `save (${cardCount} cards)`}
                </button>
                <button
                  onClick={() => {
                    setShowNameInput(false);
                    setSnapshotName("");
                  }}
                  className="btn-ghost text-xs"
                >
                  cancel
                </button>
              </div>
              {creating && (
                <p className="text-xxs text-text-muted">
                  running analytics and 1000-game simulation...
                </p>
              )}
            </div>
          )}

          {error && (
            <div className="px-2 py-1.5 bg-accent-red/10 border border-accent-red/30 rounded text-accent-red text-xs">
              {error}
              <button onClick={() => setError("")} className="ml-2 text-accent-red/60 hover:text-accent-red">✕</button>
            </div>
          )}

          {loading && (
            <div className="text-text-muted text-xs">
              loading versions<span className="animate-pulse">...</span>
            </div>
          )}

          {/* Cards grid */}
          {!loading && (
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {/* Versions — latest first, used as baseline */}
              {versionStats.map((vs, index) => (
                <StatsCard
                  key={vs.versionId}
                  stats={vs}
                  isCurrent={index === 0}
                  currentStats={index === 0 ? null : versionStats[0]}
                  onCompare={index === 0 ? undefined : () => vs.versionId && handleDiff(vs.versionId)}
                  onRestore={index === 0 ? undefined : () => vs.versionId && vs.versionNumber && handleRestore(vs.versionId, vs.versionNumber)}
                  onDelete={() => vs.versionId && vs.versionNumber && handleDelete(vs.versionId, vs.versionNumber)}
                  restoring={restoring === vs.versionId}
                  diffData={vs.versionId ? diffs[vs.versionId] || null : null}
                />
              ))}

              {versionStats.length === 0 && !loading && (
                <p className="text-xxs text-text-muted">no snapshots yet — create one to start tracking</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
"use client";

import { useState } from "react";
import GameSimChart, { type TurnData } from "./GameSimChart";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Props {
  deckId: string;
  onClose: () => void;
}

interface SimConfig {
  games: number;
  turns: number;
  minLands: number;
  maxLands: number;
}

interface TrackingConfig {
  trackTypes: string[];
  trackRoles: string[];
  trackCommander: boolean;
  trackCmcSlots: number[];
}

interface CustomMetrics {
  type_tracking?: Record<string, {
    per_turn_probability: Record<string, number>;
    per_turn_avg_count: Record<string, number>;
  }>;
  role_tracking?: Record<string, {
    per_turn_probability: Record<string, number>;
    per_turn_avg_count: Record<string, number>;
    cards_in_deck: number;
    card_names: string[];
  }>;
  commander_tracking?: {
    commander_cmc: number;
    colors_required: Record<string, number>;
    per_turn_castable_pct: Record<string, number>;
  };
  cmc_tracking?: Record<string, {
    cards_at_cmc: number;
    per_turn_can_cast_pct: Record<string, number>;
  }>;
}

interface SimResult {
  per_turn_averages: TurnData[];
  games_simulated: number;
  opening_hand_stats?: {
    mulligan_rate: number;
    avg_types: Record<string, number>;
    pct_has_ramp: number;
    pct_has_draw: number;
  };
  mulligan_settings?: {
    min_lands: number;
    max_lands: number;
  };
  custom_metrics?: CustomMetrics;
}

const AVAILABLE_TYPES = ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker"];
interface DeckRole {
  role: string;
  count: number;
  cards: string[];
}


export default function GameSimulator({ deckId, onClose }: Props) {
  const [config, setConfig] = useState<SimConfig>({
    games: 500,
    turns: 10,
    minLands: 2,
    maxLands: 5,
  });
  const [tracking, setTracking] = useState<TrackingConfig>({
    trackTypes: [],
    trackRoles: [],
    trackCommander: false,
    trackCmcSlots: [],
  });
  const [showTracking, setShowTracking] = useState(false);
  const [result, setResult] = useState<SimResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [deckRoles, setDeckRoles] = useState<DeckRole[]>([]);
  const [rolesLoaded, setRolesLoaded] = useState(false);

  function toggleType(type: string) {
    setTracking(prev => ({
      ...prev,
      trackTypes: prev.trackTypes.includes(type)
        ? prev.trackTypes.filter(t => t !== type)
        : [...prev.trackTypes, type],
    }));
  }

  function toggleRole(role: string) {
    setTracking(prev => ({
      ...prev,
      trackRoles: prev.trackRoles.includes(role)
        ? prev.trackRoles.filter(r => r !== role)
        : [...prev.trackRoles, role],
    }));
  }

  function toggleCmc(cmc: number) {
    setTracking(prev => ({
      ...prev,
      trackCmcSlots: prev.trackCmcSlots.includes(cmc)
        ? prev.trackCmcSlots.filter(c => c !== cmc)
        : [...prev.trackCmcSlots, cmc],
    }));
  }

  async function fetchDeckRoles() {
    if (rolesLoaded) return;
    try {
      const token = localStorage.getItem("mtg_token");
      const res = await fetch(`${API_BASE}/decks/${deckId}/roles`, {
        headers: { Authorization: `Bearer ${token || ""}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDeckRoles(data.roles || []);
      }
    } catch {
      // silent
    } finally {
      setRolesLoaded(true);
    }
  }

  const hasCustomTracking = tracking.trackTypes.length > 0 || tracking.trackRoles.length > 0 || tracking.trackCommander || tracking.trackCmcSlots.length > 0;

  async function runSimulation() {
    setLoading(true);
    setError("");
    setElapsed(0);

    const timer = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("mtg_token") : null;

      let data;

      if (hasCustomTracking) {
        // Use custom tracking endpoint
        const params = new URLSearchParams({
          n_games: String(config.games),
          turns: String(config.turns),
        });

        const trackingBody: Record<string, unknown> = {};
        if (tracking.trackTypes.length > 0) trackingBody.track_types = tracking.trackTypes;
        if (tracking.trackRoles.length > 0) trackingBody.track_roles = tracking.trackRoles;
        if (tracking.trackCommander) trackingBody.track_commander = { cmc: 0, colors: {} }; // Will be filled by backend
        if (tracking.trackCmcSlots.length > 0) trackingBody.track_cmc_slots = tracking.trackCmcSlots;

        const res = await fetch(`${API_BASE}/decks/${deckId}/simulate/custom?${params}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(trackingBody),
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Simulation failed: ${res.status}`);
        }

        data = await res.json();
      } else {
        // Standard simulation
        const params = new URLSearchParams({
          n_games: String(config.games),
          turns: String(config.turns),
          min_lands: String(config.minLands),
          max_lands: String(config.maxLands),
        });

        const res = await fetch(`${API_BASE}/decks/${deckId}/simulate/game?${params}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Simulation failed: ${res.status}`);
        }

        data = await res.json();
      }

      setResult({
        per_turn_averages: (data.per_turn_averages || []) as TurnData[],
        games_simulated: data.games_simulated || config.games,
        opening_hand_stats: data.opening_hand_stats,
        mulligan_settings: data.mulligan_settings,
        custom_metrics: data.custom_metrics,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      clearInterval(timer);
      setLoading(false);
    }
  }

  const ohs = result?.opening_hand_stats;
  const cm = result?.custom_metrics;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="panel p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-xs text-text-muted font-medium uppercase tracking-wider">
              Game Simulator
            </div>
            <div className="text-xxs text-text-muted mt-0.5">
              goldfish simulation — no opponents, just your deck vs the clock
            </div>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            ✕
          </button>
        </div>

        {/* Configuration */}
        {!result && !loading && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-text-secondary mb-1.5">
                  number of games
                </label>
                <select
                  value={config.games}
                  onChange={(e) => setConfig({ ...config, games: Number(e.target.value) })}
                  className="input-terminal"
                >
                  <option value={100}>100 games (fast)</option>
                  <option value={250}>250 games</option>
                  <option value={500}>500 games (recommended)</option>
                  <option value={1000}>1000 games (thorough)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-secondary mb-1.5">
                  turns to simulate
                </label>
                <select
                  value={config.turns}
                  onChange={(e) => setConfig({ ...config, turns: Number(e.target.value) })}
                  className="input-terminal"
                >
                  <option value={5}>5 turns (early game)</option>
                  <option value={7}>7 turns</option>
                  <option value={10}>10 turns (recommended)</option>
                  <option value={15}>15 turns (late game)</option>
                </select>
              </div>
            </div>

            {/* Mulligan conditions */}
            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                mulligan conditions
              </label>
              <div className="text-xxs text-text-muted mb-2">
                mulligan if opening hand has fewer than min or more than max lands
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xxs text-text-muted mb-1">
                    min lands to keep
                  </label>
                  <select
                    value={config.minLands}
                    onChange={(e) => setConfig({ ...config, minLands: Number(e.target.value) })}
                    className="input-terminal"
                  >
                    {[0, 1, 2, 3, 4].map((n) => (
                      <option key={n} value={n}>
                        {n} land{n !== 1 ? "s" : ""} {n === 2 ? "(default)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xxs text-text-muted mb-1">
                    max lands to keep
                  </label>
                  <select
                    value={config.maxLands}
                    onChange={(e) => setConfig({ ...config, maxLands: Number(e.target.value) })}
                    className="input-terminal"
                  >
                    {[3, 4, 5, 6, 7].map((n) => (
                      <option key={n} value={n}>
                        {n} lands {n === 5 ? "(default)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Custom Tracking */}
            <div className="border-t border-border pt-3">
              <button
                onClick={() => {
                  setShowTracking(!showTracking);
                  if (!showTracking) fetchDeckRoles();
                }}
                className="text-xs text-text-muted hover:text-text-secondary transition-colors"
              >
                {showTracking ? "▲ hide" : "▼ show"} custom tracking options
              </button>

              {showTracking && (
                <div className="mt-3 space-y-3">
                  {/* Card Type Tracking */}
                  <div>
                    <span className="text-xxs text-text-muted uppercase tracking-wider">track card types drawn</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {AVAILABLE_TYPES.map(type => (
                        <button
                          key={type}
                          onClick={() => toggleType(type)}
                          className={`text-xxs px-2 py-1 rounded border transition-colors ${
                            tracking.trackTypes.includes(type)
                              ? "border-accent-green text-accent-green bg-accent-green/10"
                              : "border-border text-text-muted hover:text-text-secondary"
                          }`}
                        >
                          {type}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Role Tracking — dynamic from user-tagged cards */}
                  <div>
                    <span className="text-xxs text-text-muted uppercase tracking-wider">track role availability</span>
                    {deckRoles.length > 0 ? (
                      <div className="flex flex-wrap gap-2 mt-1">
                        {deckRoles.map(dr => (
                          <button
                            key={dr.role}
                            onClick={() => toggleRole(dr.role)}
                            className={`text-xxs px-2 py-1 rounded border transition-colors ${
                              tracking.trackRoles.includes(dr.role)
                                ? "border-accent-green text-accent-green bg-accent-green/10"
                                : "border-border text-text-muted hover:text-text-secondary"
                            }`}
                          >
                            {dr.role.replace("_", " ")} ({dr.count})
                          </button>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xxs text-text-muted mt-1">
                        no roles tagged yet — expand cards in the deck list and assign roles to enable tracking
                      </p>
                    )}
                  </div>

                  {/* Commander Castability */}
                  <div>
                    <button
                      onClick={() => setTracking(prev => ({ ...prev, trackCommander: !prev.trackCommander }))}
                      className={`text-xxs px-2 py-1 rounded border transition-colors ${
                        tracking.trackCommander
                          ? "border-accent-green text-accent-green bg-accent-green/10"
                          : "border-border text-text-muted hover:text-text-secondary"
                      }`}
                    >
                      track commander castability
                    </button>
                  </div>

                  

                  {hasCustomTracking && (
                    <p className="text-xxs text-accent-green">
                      custom tracking enabled — simulation will include additional metrics
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="text-xxs text-text-muted space-y-1">
              <p>simulates full turns: draw, play land, cast spells in priority order</p>
              <p>ramp spells resolve and accelerate mana, draw spells pull extra cards</p>
              <p>does NOT simulate: combat damage triggers, attack triggers, opponent interaction</p>
              <p>measures deck consistency — how reliably your engine starts up</p>
            </div>

            {error && (
              <div className="px-3 py-2 bg-accent-red/10 border border-accent-red/30 rounded text-accent-red text-sm">
                {error}
              </div>
            )}

            <button onClick={runSimulation} className="btn-primary w-full">
              run simulation →
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="text-center py-12">
            <div className="text-text-muted text-sm mb-2">
              <span className="text-accent-green">$</span> simulating {config.games} games over {config.turns} turns...
              <span className="animate-pulse">█</span>
            </div>
            <div className="text-text-muted text-xs">{elapsed}s elapsed</div>
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <div className="space-y-4">
            {/* Summary banner */}
            <div className="bg-bg-primary border border-border rounded p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">
                  {result.games_simulated} games × {result.per_turn_averages.length} turns
                </span>
                <button
                  onClick={() => setResult(null)}
                  className="btn-ghost text-xs"
                >
                  new run
                </button>
              </div>
            </div>

            {/* Opening hand stats */}
            {ohs && (
              <div className="bg-bg-primary border border-border rounded p-3">
                <div className="text-xxs text-text-muted font-medium uppercase tracking-wider mb-2">
                  Opening Hand
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                  <div>
                    <div className={`text-lg font-bold ${ohs.mulligan_rate <= 20 ? "text-accent-green" : ohs.mulligan_rate <= 30 ? "text-accent-yellow" : "text-accent-red"}`}>
                      {ohs.mulligan_rate}%
                    </div>
                    <div className="text-xxs text-text-muted">mulligan rate</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold text-accent-green">
                      {ohs.avg_types?.Land?.toFixed(1) || "0"}
                    </div>
                    <div className="text-xxs text-text-muted">avg lands</div>
                  </div>
                  <div>
                    <div className={`text-lg font-bold ${ohs.pct_has_ramp >= 60 ? "text-accent-green" : ohs.pct_has_ramp >= 40 ? "text-accent-yellow" : "text-accent-red"}`}>
                      {ohs.pct_has_ramp}%
                    </div>
                    <div className="text-xxs text-text-muted">has ramp</div>
                  </div>
                  <div>
                    <div className={`text-lg font-bold ${ohs.pct_has_draw >= 40 ? "text-accent-green" : ohs.pct_has_draw >= 25 ? "text-accent-yellow" : "text-accent-red"}`}>
                      {ohs.pct_has_draw}%
                    </div>
                    <div className="text-xxs text-text-muted">has draw</div>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-border/50 flex flex-wrap gap-3 justify-center">
                  {Object.entries(ohs.avg_types || {})
                    .sort(([, a], [, b]) => b - a)
                    .map(([type, avg]) => (
                      <div key={type} className="text-center">
                        <div className="text-xs text-text-primary">{avg.toFixed(1)}</div>
                        <div className="text-xxs text-text-muted">{type}</div>
                      </div>
                    ))}
                </div>
                {result.mulligan_settings && (
                  <div className="mt-2 text-xxs text-text-muted text-center">
                    mulligan if lands &lt; {result.mulligan_settings.min_lands} or &gt; {result.mulligan_settings.max_lands}
                  </div>
                )}
              </div>
            )}

            {/* Key insights at a glance */}
            {result.per_turn_averages.length >= 5 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {(() => {
                  const t3 = result.per_turn_averages[2];
                  const t5 = result.per_turn_averages[4];
                  const t7 = result.per_turn_averages.length >= 7 ? result.per_turn_averages[6] : null;
                  const rampT5 = (t5?.avg_total_mana_available || 0) - (t5?.avg_lands_on_board || 0);
                  return (
                    <>
                      <div className="panel p-3 text-center">
                        <div className={`text-lg font-bold ${(t3?.mana_on_curve_rate || 0) >= 80 ? "text-accent-green" : (t3?.mana_on_curve_rate || 0) >= 65 ? "text-accent-yellow" : "text-accent-red"}`}>
                          {(t3?.mana_on_curve_rate || 0).toFixed(0)}%
                        </div>
                        <div className="text-xxs text-text-muted">on curve T3</div>
                      </div>
                      <div className="panel p-3 text-center">
                        <div className={`text-lg font-bold ${rampT5 >= 1.5 ? "text-accent-green" : rampT5 >= 0.5 ? "text-accent-yellow" : "text-accent-red"}`}>
                          +{rampT5.toFixed(1)}
                        </div>
                        <div className="text-xxs text-text-muted">ramp by T5</div>
                      </div>
                      <div className="panel p-3 text-center">
                        <div className={`text-lg font-bold ${(t5?.all_colors_rate || 0) >= 75 ? "text-accent-green" : (t5?.all_colors_rate || 0) >= 50 ? "text-accent-yellow" : "text-accent-red"}`}>
                          {(t5?.all_colors_rate || 0).toFixed(0)}%
                        </div>
                        <div className="text-xxs text-text-muted">all colors T5</div>
                      </div>
                      <div className="panel p-3 text-center">
                        <div className={`text-lg font-bold ${(t7?.avg_total_power_on_board || 0) >= 15 ? "text-accent-green" : (t7?.avg_total_power_on_board || 0) >= 8 ? "text-accent-yellow" : "text-accent-red"}`}>
                          {(t7?.avg_total_power_on_board || 0).toFixed(0)}
                        </div>
                        <div className="text-xxs text-text-muted">power T7</div>
                      </div>
                    </>
                  );
                })()}
              </div>
            )}

            {/* Full tabbed stats */}
            <GameSimChart
              turnData={result.per_turn_averages}
              gamesSimulated={result.games_simulated}
            />

            {/* Custom Metrics Results */}
            {cm && (
              <div className="space-y-3">
                <div className="text-xxs text-text-muted font-medium uppercase tracking-wider">
                  Custom Tracking Results
                </div>

                {/* Type Tracking */}
                {cm.type_tracking && Object.entries(cm.type_tracking).map(([type, data]) => {
                  const d = data as Record<string, unknown>;
                  const drawnPct = (d.per_turn_drawn_pct || d.per_turn_probability || {}) as Record<string, number>;
                  const hasAnyData = Object.values(drawnPct).some(v => v > 0);
                  if (!hasAnyData) return null;
                  const castablePct = d.per_turn_castable_pct as Record<string, number> | undefined;
                  return (
                    <div key={type} className="bg-bg-primary border border-border rounded p-3">
                      <div className="text-xs text-text-primary font-medium mb-2">{type} by turn</div>
                      <div className="text-xxs text-text-muted mb-1">drawn</div>
                      <div className="flex gap-1 flex-wrap">
                        {Object.entries(drawnPct).map(([turn, pct]) => (
                          <div key={turn} className="text-center min-w-[40px]">
                            <div className={`text-xs font-bold ${pct >= 80 ? "text-accent-green" : pct >= 50 ? "text-accent-yellow" : "text-accent-red"}`}>
                              {pct}%
                            </div>
                            <div className="text-xxs text-text-muted">T{turn}</div>
                          </div>
                        ))}
                      </div>
                      {castablePct && (
                        <>
                          <div className="text-xxs text-text-muted mt-2 mb-1">castable in hand <span className="text-text-muted/50">(drops as cards are cast)</span></div>
                          <div className="flex gap-1 flex-wrap">
                            {Object.entries(castablePct).map(([turn, pct]) => (
                              <div key={turn} className="text-center min-w-[40px]">
                                <div className={`text-xs font-bold ${pct >= 80 ? "text-accent-green" : pct >= 50 ? "text-accent-yellow" : "text-accent-red"}`}>
                                  {pct}%
                                </div>
                                <div className="text-xxs text-text-muted">T{turn}</div>
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}

                {/* Role Tracking */}
                {cm.role_tracking && Object.entries(cm.role_tracking).map(([role, data]) => {
                  const d = data as Record<string, unknown>;
                  const drawnPct = (d.per_turn_drawn_pct || {}) as Record<string, number>;
                  const castablePct = d.per_turn_castable_pct as Record<string, number> | undefined;
                  const cardNames = (d.card_names || []) as string[];
                  const cardsInDeck = (d.cards_in_deck || 0) as number;
                  const hasDrawnData = Object.values(drawnPct).some(v => v > 0);

                  return (
                    <div key={role} className="bg-bg-primary border border-border rounded p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-text-primary font-medium">{role.replace("_", " ")}</span>
                        <span className="text-xxs text-text-muted">{cardsInDeck} cards in deck</span>
                      </div>
                      {hasDrawnData ? (
                        <>
                          <div className="text-xxs text-text-muted mb-1">drawn</div>
                          <div className="flex gap-1 flex-wrap">
                            {Object.entries(drawnPct).map(([turn, pct]) => (
                              <div key={turn} className="text-center min-w-[40px]">
                                <div className={`text-xs font-bold ${pct >= 80 ? "text-accent-green" : pct >= 50 ? "text-accent-yellow" : "text-accent-red"}`}>
                                  {pct}%
                                </div>
                                <div className="text-xxs text-text-muted">T{turn}</div>
                              </div>
                            ))}
                          </div>
                          {castablePct && Object.values(castablePct).some(v => v > 0) && (
                            <>
                              <div className="text-xxs text-text-muted mt-2 mb-1">castable in hand <span className="text-text-muted/50">(drops as cards are cast)</span></div>
                              <div className="flex gap-1 flex-wrap">
                                {Object.entries(castablePct).map(([turn, pct]) => (
                                  <div key={turn} className="text-center min-w-[40px]">
                                    <div className={`text-xs font-bold ${pct >= 80 ? "text-accent-green" : pct >= 50 ? "text-accent-yellow" : "text-accent-red"}`}>
                                      {pct}%
                                    </div>
                                    <div className="text-xxs text-text-muted">T{turn}</div>
                                  </div>
                                ))}
                              </div>
                            </>
                          )}
                        </>
                      ) : (
                        <div className="text-xxs text-text-muted">
                          per-turn tracking not available — card count only
                        </div>
                      )}
                      {cardNames.length > 0 && (
                        <div className="mt-2 text-xxs text-text-muted">
                          cards: {cardNames.map(n => n.split(" // ")[0]).join(", ")}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Commander Tracking */}
                {cm.commander_tracking && (
                  <div className="bg-bg-primary border border-border rounded p-3">
                    <div className="text-xs text-text-primary font-medium mb-2">
                      {(cm.commander_tracking as Record<string, unknown>).name
                        ? `${(cm.commander_tracking as Record<string, unknown>).name} castability (CMC ${cm.commander_tracking.commander_cmc})`
                        : `commander castability (CMC ${cm.commander_tracking.commander_cmc})`
                      }
                    </div>
                    <div className="flex gap-1 flex-wrap">
                      {Object.entries(cm.commander_tracking.per_turn_castable_pct).map(([turn, pct]) => (
                        <div key={turn} className="text-center min-w-[40px]">
                          <div className={`text-xs font-bold ${pct >= 80 ? "text-accent-green" : pct >= 50 ? "text-accent-yellow" : "text-accent-red"}`}>
                            {pct}%
                          </div>
                          <div className="text-xxs text-text-muted">T{turn}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Run again */}
            <div className="flex gap-3 justify-center pt-2">
              <button onClick={() => setResult(null)} className="btn-ghost">
                change settings
              </button>
              <button onClick={runSimulation} className="btn-primary">
                run again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
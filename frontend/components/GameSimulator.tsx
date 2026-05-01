"use client";

import { useState } from "react";
import { simulateGame } from "@/lib/api";
import GameSimChart, { type TurnData } from "./GameSimChart";

interface Props {
  deckId: string;
  onClose: () => void;
}

interface SimConfig {
  games: number;
  turns: number;
}

interface SimResult {
  per_turn_averages: TurnData[];
  games_simulated: number;
}

export default function GameSimulator({ deckId, onClose }: Props) {
  const [config, setConfig] = useState<SimConfig>({ games: 500, turns: 10 });
  const [result, setResult] = useState<SimResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");

  async function runSimulation() {
    setLoading(true);
    setError("");
    setElapsed(0);

    const timer = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    try {
      const data = await simulateGame(deckId, config.games);
      setResult({
        per_turn_averages: (data.per_turn_averages || []) as TurnData[],
        games_simulated: (data.games_simulated || config.games) as number,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      clearInterval(timer);
      setLoading(false);
    }
  }

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

            <div className="text-xxs text-text-muted space-y-1">
              <p>simulates drawing cards, playing lands, and casting spells each turn</p>
              <p>tracks: mana development, board state, color access, castability</p>
              <p>no combat or opponent interaction — pure deck consistency analysis</p>
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
                  {result.games_simulated} games simulated over {result.per_turn_averages.length} turns
                </span>
                <button
                  onClick={() => setResult(null)}
                  className="btn-ghost text-xs"
                >
                  configure new run
                </button>
              </div>
            </div>

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
"use client";

import { useState, useEffect } from "react";
import { getAnalytics, getStrategy } from "@/lib/api";
import ManaCurveChart from "./ManaCurveChart";
import ColorDistributionChart from "./ColorDistributionChart";
import TypeDistributionChart from "./TypeDistributionChart";
import ColorHealthChart from "./ColorHealthChart";
import GameSimChart, { type TurnData } from "./GameSimChart";

interface Props {
  deckId: string;
  cardCount: number;
}

export default function DeckAnalytics({ deckId, cardCount }: Props) {
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null);
  const [strategy, setStrategy] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      if (cardCount === 0) {
        setLoading(false);
        return;
      }

      try {
        const [analyticsResult, strategyResult] = await Promise.allSettled([
          getAnalytics(deckId),
          getStrategy(deckId),
        ]);

        if (analyticsResult.status === "fulfilled") {
          setAnalytics(analyticsResult.value as unknown as Record<string, unknown>);
        }
        if (strategyResult.status === "fulfilled" && strategyResult.value) {
          setStrategy(strategyResult.value);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load analytics");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [deckId, cardCount]);

  if (cardCount === 0) {
    return (
      <div className="panel p-4 text-center">
        <p className="text-text-muted text-xs">add cards to see analytics</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="panel p-4">
        <div className="text-text-muted text-xs">
          <span className="text-accent-green">$</span> loading analytics...
          <span className="animate-pulse">█</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel p-4">
        <div className="text-accent-red text-xs">error: {error}</div>
      </div>
    );
  }

  // Parse analytics data
  const manaCurve = (analytics?.mana_curve || {}) as Record<string, number>;
  const colorDist = (analytics?.color_distribution || {}) as Record<string, { name: string; count: number }>;
  const typeDist = (analytics?.type_distribution || {}) as Record<string, number>;
  const averageCmc = (analytics?.average_cmc || 0) as number;
  const totalCards = (analytics?.total_cards || cardCount) as number;

  // Derive land/nonland from type distribution
  const landCount = typeDist["Land"] || 0;
  const nonlandCount = totalCards - landCount;

  // Parse strategy data
  const colorHealth = strategy?.color_health as {
    color_health: Record<string, { score: number; sim_access: number; sources: number; pips: number; adequacy: number }>;
    fix_priority: string[];
    overall_health: number;
  } | undefined;

  const cachedSim = strategy?.cached_simulation as {
    per_turn_averages: TurnData[];
    games_simulated: number;
  } | undefined;

  // Estimated deck value from strategy profile impact ratings
  const impactRatings = (strategy?.card_impact_ratings || []) as Array<{ card_name: string; score: number }>;
  const avgImpact = impactRatings.length > 0
    ? (impactRatings.reduce((sum, r) => sum + r.score, 0) / impactRatings.length).toFixed(1)
    : null;

  return (
    <div className="space-y-4">
      {/* Quick Stats */}
      <div className="panel p-4">
        <div className="text-xxs text-text-muted font-medium uppercase tracking-wider mb-3">
          Quick Stats
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">total</span>
            <span className="text-text-primary">{totalCards}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">avg cmc</span>
            <span className="text-text-primary">{averageCmc.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">lands</span>
            <span className="text-text-primary">{landCount}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">nonland</span>
            <span className="text-text-primary">{nonlandCount}</span>
          </div>
          {avgImpact && (
            <div className="flex justify-between col-span-2 pt-1.5 border-t border-border">
              <span className="text-text-secondary">avg impact</span>
              <span className="text-text-primary">{avgImpact}/10</span>
            </div>
          )}
          {colorHealth && (
            <div className="flex justify-between col-span-2">
              <span className="text-text-secondary">mana health</span>
              <span className={`${colorHealth.overall_health >= 80 ? "text-accent-green" : colorHealth.overall_health >= 70 ? "text-accent-yellow" : "text-accent-red"}`}>
                {colorHealth.overall_health.toFixed(0)}%
              </span>
            </div>
          )}
          {cachedSim && (
            <div className="flex justify-between col-span-2">
              <span className="text-text-secondary">games simulated</span>
              <span className="text-text-primary">{cachedSim.games_simulated}</span>
            </div>
          )}
        </div>
      </div>

      {/* Mana Curve */}
      <div className="panel p-4">
        <ManaCurveChart manaCurve={manaCurve} averageCmc={averageCmc} />
      </div>

      {/* Color Distribution */}
      <div className="panel p-4">
        <ColorDistributionChart colorDistribution={colorDist} />
      </div>

      {/* Color Health — from strategy profile */}
      {colorHealth && (
        <div className="panel p-4">
          <ColorHealthChart
            colorHealth={colorHealth.color_health}
            fixPriority={colorHealth.fix_priority}
            overallHealth={colorHealth.overall_health}
          />
        </div>
      )}

      {/* Type Distribution */}
      <div className="panel p-4">
        <TypeDistributionChart typeDistribution={typeDist} totalCards={totalCards} />
      </div>

      {/* Simulation — from cached simulation */}
      {cachedSim && cachedSim.per_turn_averages && cachedSim.per_turn_averages.length > 0 && (
        <div className="panel p-4">
          <GameSimChart
            turnData={cachedSim.per_turn_averages}
            gamesSimulated={cachedSim.games_simulated}
          />
        </div>
      )}

      {/* No strategy profile notice */}
      {!strategy && (
        <div className="panel p-4 text-center">
          <p className="text-text-muted text-xs">
            generate a strategy profile to see color health, simulation data, and card impact scores
          </p>
        </div>
      )}
    </div>
  );
}
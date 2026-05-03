"use client";

import { useState, useEffect } from "react";
import { getStrategy, streamStrategy } from "@/lib/api";

interface Props {
  deckId: string;
  hasProfile: boolean;
  onComplete: () => void;
}

interface ProgressStep {
  step: string;
  progress: number;
  message: string;
}

export default function StrategyGenerator({ deckId, hasProfile, onComplete }: Props) {
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState<ProgressStep | null>(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (hasProfile) {
      getStrategy(deckId).then((data) => {
        if (data) setProfile(data);
      });
    }
  }, [hasProfile, deckId]);

  function handleGenerate() {
    setGenerating(true);
    setError("");
    setProgress({ step: "starting", progress: 0, message: "Initializing..." });

    streamStrategy(
      deckId,
      (event) => setProgress(event),
      () => {
        setGenerating(false);
        setProgress(null);
        onComplete();
      },
      (err) => {
        setGenerating(false);
        setProgress(null);
        setError(err);
      }
    );
  }

  const strategy = profile?.primary_strategy as string | undefined;
  const commanderRole = profile?.commander_role as string | undefined;
  const winConditions = profile?.win_conditions as string[] | undefined;
  const synergies = profile?.key_synergies as Array<{ cards: string[]; description: string }> | undefined;
  const criticalCards = profile?.critical_cards as string[] | undefined;
  const weaknesses = profile?.weaknesses as string[] | undefined;
  const roleNeeds = profile?.role_needs as { needs_more?: string[]; has_enough?: string[]; over_saturated?: string[] } | undefined;
  const upgradePriorities = profile?.upgrade_priorities as string[] | undefined;

  return (
    <div className="panel">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-bg-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted font-medium uppercase tracking-wider">
            Strategy Profile
          </span>
          {hasProfile && !generating && (
            <span className="text-xxs text-accent-green">generated</span>
          )}
        </div>
        <span className="text-text-muted text-xs">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          {/* Generate/Regenerate button */}
          {!generating && (
            <div className="mb-3">
              <button
                onClick={handleGenerate}
                className={hasProfile ? "btn-ghost text-xs w-full" : "btn-primary text-xs w-full"}
              >
                {hasProfile ? "regenerate profile" : "generate strategy profile →"}
              </button>
              {!hasProfile && (
                <p className="text-xxs text-text-muted mt-1">
                  AI analyzes every card, ranks impact, maps synergies, runs simulation
                </p>
              )}
            </div>
          )}

          {/* Progress bar */}
          {generating && progress && (
            <div className="space-y-2 mb-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-text-secondary">{progress.message}</span>
                <span className="text-text-muted">{progress.progress}%</span>
              </div>
              <div className="w-full h-1.5 bg-bg-primary rounded overflow-hidden">
                <div
                  className="h-full bg-accent-green rounded transition-all duration-300"
                  style={{ width: `${progress.progress}%` }}
                />
              </div>
              <div className="text-xxs text-text-muted">
                takes 1-2 minutes
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mb-3 px-3 py-2 bg-accent-red/10 border border-accent-red/30 rounded text-accent-red text-xs">
              {error}
              <button onClick={() => setError("")} className="ml-2 text-accent-red/60 hover:text-accent-red">✕</button>
            </div>
          )}

          {/* Profile content */}
          {profile && !generating && (
            <div className="space-y-3 text-xs">
              {/* Commander Role */}
              {commanderRole && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">commander role</span>
                  <p className="text-text-secondary mt-0.5">{commanderRole}</p>
                </div>
              )}

              {/* Primary Strategy */}
              {strategy && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">strategy</span>
                  <p className="text-text-secondary mt-0.5">{strategy}</p>
                </div>
              )}

              {/* Win Conditions */}
              {winConditions && winConditions.length > 0 && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">win conditions</span>
                  <div className="mt-0.5 space-y-0.5">
                    {winConditions.map((wc, i) => (
                      <div key={i} className="flex items-start gap-1.5">
                        <span className="text-accent-green flex-shrink-0">→</span>
                        <span className="text-text-secondary">{wc}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Critical Cards */}
              {criticalCards && criticalCards.length > 0 && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">critical cards</span>
                  <p className="text-text-secondary mt-0.5">{criticalCards.join(", ")}</p>
                </div>
              )}

              {/* Key Synergies */}
              {synergies && synergies.length > 0 && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">key synergies</span>
                  <div className="mt-0.5 space-y-1">
                    {synergies.slice(0, 5).map((syn, i) => (
                      <div key={i}>
                        <span className="text-text-primary">{syn.cards.join(" + ")}</span>
                        <span className="text-text-muted"> — {syn.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Weaknesses */}
              {weaknesses && weaknesses.length > 0 && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">weaknesses</span>
                  <div className="mt-0.5 space-y-0.5">
                    {weaknesses.map((w, i) => (
                      <div key={i} className="flex items-start gap-1.5">
                        <span className="text-accent-red flex-shrink-0">!</span>
                        <span className="text-text-secondary">{w}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Role Needs */}
              {roleNeeds && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">role assessment</span>
                  <div className="mt-0.5 space-y-0.5">
                    {roleNeeds.needs_more && roleNeeds.needs_more.length > 0 && (
                      <div className="flex items-start gap-1.5">
                        <span className="text-accent-yellow flex-shrink-0">↑</span>
                        <span className="text-text-secondary">needs more: {roleNeeds.needs_more.join(", ")}</span>
                      </div>
                    )}
                    {roleNeeds.over_saturated && roleNeeds.over_saturated.length > 0 && (
                      <div className="flex items-start gap-1.5">
                        <span className="text-accent-red flex-shrink-0">↓</span>
                        <span className="text-text-secondary">over-saturated: {roleNeeds.over_saturated.join(", ")}</span>
                      </div>
                    )}
                    {roleNeeds.has_enough && roleNeeds.has_enough.length > 0 && (
                      <div className="flex items-start gap-1.5">
                        <span className="text-accent-green flex-shrink-0">✓</span>
                        <span className="text-text-secondary">sufficient: {roleNeeds.has_enough.join(", ")}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Upgrade Priorities */}
              {upgradePriorities && upgradePriorities.length > 0 && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">upgrade priorities</span>
                  <div className="mt-0.5 space-y-0.5">
                    {upgradePriorities.map((up, i) => (
                      <div key={i} className="flex items-start gap-1.5">
                        <span className="text-text-muted flex-shrink-0">{i + 1}.</span>
                        <span className="text-text-secondary">{up}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
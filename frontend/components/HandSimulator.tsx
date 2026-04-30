"use client";

import { useState } from "react";
import { simulateHand } from "@/lib/api";

interface HandCard {
  card_name: string;
  scryfall_id: string;
  quantity: number;
  board: string;
}

interface HandResult {
  hand: string[];
  land_count: number;
  nonland_count: number;
}

interface SimStats {
  avg_lands: number;
  land_distribution: Record<string, number>;
}

interface Props {
  deckId: string;
  onClose: () => void;
}

function CardInHand({ name, scryfallId }: { name: string; scryfallId?: string }) {
  const [imgError, setImgError] = useState(false);

  return (
    <div className="flex-shrink-0 group relative">
      {scryfallId && !imgError ? (
        <img
          src={`https://api.scryfall.com/cards/${scryfallId}?format=image&version=normal`}
          alt={name}
          className="w-32 rounded shadow-lg hover:scale-110 hover:z-10 transition-transform cursor-pointer"
          onError={() => setImgError(true)}
          loading="lazy"
        />
      ) : (
        <div className="w-32 h-44 rounded bg-bg-tertiary border border-border flex items-center justify-center p-2">
          <span className="text-xxs text-text-secondary text-center">{name}</span>
        </div>
      )}
    </div>
  );
}

export default function HandSimulator({ deckId, onClose }: Props) {
  const [hand, setHand] = useState<HandResult | null>(null);
  const [stats, setStats] = useState<SimStats | null>(null);
  const [mulliganCount, setMulliganCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cardLookup, setCardLookup] = useState<Record<string, string>>({});

  async function drawHand() {
    setLoading(true);
    setError("");

    try {
      const result = await simulateHand(deckId, 1);

      // Build scryfall_id lookup from the raw response
      if (result.hands && result.hands.length > 0) {
        const firstHand = result.hands[0];
        setHand({
          hand: firstHand.cards || [],
          land_count: firstHand.land_count || 0,
          nonland_count: firstHand.nonland_count || 0,
        });
      }

      if (result.statistics) {
        setStats({
          avg_lands: result.statistics.avg_lands || 0,
          land_distribution: result.statistics.land_distribution || {},
        });
      }

      // card_lookup may not be in the response — that's ok
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to simulate hand");
    } finally {
      setLoading(false);
    }
  }

  async function mulligan() {
    setMulliganCount((prev) => prev + 1);
    await drawHand();
  }

  async function keepHand() {
    // Reset for a new simulation
    setHand(null);
    setMulliganCount(0);
  }

  // Draw initial hand on mount
  if (!hand && !loading && !error) {
    drawHand();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="panel p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-xs text-text-muted font-medium uppercase tracking-wider">
              Opening Hand Simulator
            </div>
            {mulliganCount > 0 && (
              <div className="text-xxs text-text-muted mt-0.5">
                mulligan #{mulliganCount} — drawing {7 - mulliganCount} cards
              </div>
            )}
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            ✕
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <div className="text-center py-12">
            <div className="text-text-muted text-sm">
              <span className="text-accent-green">$</span> shuffling deck...
              <span className="animate-pulse">█</span>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-4 px-3 py-2 bg-accent-red/10 border border-accent-red/30 rounded text-accent-red text-sm">
            {error}
          </div>
        )}

        {/* Hand display */}
        {hand && !loading && (
          <>
            <div className="flex gap-2 overflow-x-auto pb-4 justify-center">
              {hand.hand.map((cardName, i) => (
                <CardInHand
                  key={`${cardName}-${i}`}
                  name={cardName}
                  scryfallId={cardLookup[cardName]}
                />
              ))}
            </div>

            {/* Hand stats */}
            <div className="flex items-center justify-center gap-6 my-4 text-sm">
              <div className="flex items-center gap-1.5">
                <span className="text-accent-green">●</span>
                <span className="text-text-secondary">
                  {hand.land_count} land{hand.land_count !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-accent-blue">●</span>
                <span className="text-text-secondary">
                  {hand.nonland_count} spell{hand.nonland_count !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="text-text-muted text-xs">
                {hand.hand.length} cards
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3 justify-center mb-4">
              <button
                onClick={mulligan}
                disabled={mulliganCount >= 6 || loading}
                className="btn-danger"
              >
                mulligan ({7 - mulliganCount - 1} cards)
              </button>
              <button onClick={keepHand} className="btn-primary">
                keep — draw new
              </button>
            </div>
          </>
        )}

        {/* Probability stats */}
        {stats && (
          <div className="border-t border-border pt-4">
            <div className="text-xxs text-text-muted font-medium uppercase tracking-wider mb-2">
              Land Probability (1000 hands)
            </div>
            <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
              {Object.entries(stats.land_distribution)
                .sort(([a], [b]) => Number(a) - Number(b))
                .map(([lands, pct]) => (
                  <div key={lands} className="text-center">
                    <div className="text-lg font-bold text-text-primary">{lands}</div>
                    <div className="text-xxs text-text-muted">lands</div>
                    <div className={`text-xs font-medium mt-0.5 ${
                      Number(lands) >= 2 && Number(lands) <= 4
                        ? "text-accent-green"
                        : "text-text-secondary"
                    }`}>
                      {typeof pct === "number" ? pct.toFixed(1) : pct}%
                    </div>
                  </div>
                ))}
            </div>
            <div className="text-center mt-2 text-xs text-text-muted">
              avg lands in opening hand: {stats.avg_lands.toFixed(2)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
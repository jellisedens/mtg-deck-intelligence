"use client";

import { useState, useEffect } from "react";
import { DeckCard } from "@/lib/types";

interface Props {
  deckId: string;
  cards: DeckCard[];
  onClose: () => void;
}

function CardInHand({ name, scryfallId }: { name: string; scryfallId: string }) {
  const [imgError, setImgError] = useState(false);

  return (
    <div className="flex-shrink-0">
      {!imgError ? (
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

function shuffle<T>(arr: T[]): T[] {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

function isLand(card: DeckCard): boolean {
  if (card.ai_context?.role === "land") return true;
  const lower = card.card_name.toLowerCase();
  const landWords = [
    "forest", "mountain", "plains", "island", "swamp",
    "bog", "glade", "vista", "stream", "hollow", "marsh",
    "foundry", "vents", "tomb", "grave", "garden", "fountain",
    "shrine", "crypt", "tower", "orchard", "territory",
    "passage", "pool", "haven", "path of ancestry",
  ];
  return landWords.some((w) => lower.includes(w));
}

function buildPool(cards: DeckCard[]): DeckCard[] {
  const pool: DeckCard[] = [];
  for (const card of cards) {
    if (card.board === "sideboard") continue;
    for (let i = 0; i < card.quantity; i++) {
      pool.push(card);
    }
  }
  return pool;
}

export default function HandSimulator({ deckId, cards, onClose }: Props) {
  const [hand, setHand] = useState<DeckCard[]>([]);
  const [mulliganCount, setMulliganCount] = useState(0);
  const [handHistory, setHandHistory] = useState<{ lands: number; spells: number }[]>([]);

  function drawHand(drawCount?: number) {
    const count = drawCount ?? 7;
    const pool = buildPool(cards);
    const shuffled = shuffle(pool);
    setHand(shuffled.slice(0, count));
  }

  function mulligan() {
    const newCount = mulliganCount + 1;
    if (7 - newCount < 1) return;
    setMulliganCount(newCount);
    drawHand(7 - newCount);
  }

  function keepAndRedraw() {
    const lands = hand.filter(isLand).length;
    const spells = hand.length - lands;
    setHandHistory((prev) => [...prev, { lands, spells }]);
    setMulliganCount(0);
    drawHand();
  }

  useEffect(() => {
    drawHand();
  }, []);

  const landCount = hand.filter(isLand).length;
  const spellCount = hand.length - landCount;
  const totalHands = handHistory.length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="panel p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-xs text-text-muted font-medium uppercase tracking-wider">
              Opening Hand Simulator
            </div>
            {mulliganCount > 0 && (
              <div className="text-xxs text-accent-yellow mt-0.5">
                mulligan #{mulliganCount} — drawing {7 - mulliganCount} cards
              </div>
            )}
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            ✕
          </button>
        </div>

        <div className="flex gap-2 overflow-x-auto pb-4 justify-center">
          {hand.map((card, i) => (
            <CardInHand
              key={`${card.scryfall_id}-${i}`}
              name={card.card_name}
              scryfallId={card.scryfall_id}
            />
          ))}
        </div>

        <div className="flex items-center justify-center gap-6 my-4 text-sm">
          <div className="flex items-center gap-1.5">
            <span className="text-accent-green">●</span>
            <span className="text-text-secondary">
              {landCount} land{landCount !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-accent-blue">●</span>
            <span className="text-text-secondary">
              {spellCount} spell{spellCount !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="text-text-muted text-xs">
            {hand.length} cards drawn
          </div>
        </div>

        <div className="flex gap-3 justify-center mb-4">
          <button
            onClick={mulligan}
            disabled={mulliganCount >= 6}
            className="btn-danger"
          >
            mulligan ({Math.max(7 - mulliganCount - 1, 0)} cards)
          </button>
          <button onClick={keepAndRedraw} className="btn-primary">
            keep — draw new hand
          </button>
        </div>

        {totalHands > 0 && (
          <div className="border-t border-border pt-4">
            <div className="text-xxs text-text-muted font-medium uppercase tracking-wider mb-2">
              Session Stats ({totalHands} hand{totalHands !== 1 ? "s" : ""} kept)
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-lg font-bold text-accent-green">
                  {(handHistory.reduce((sum, h) => sum + h.lands, 0) / totalHands).toFixed(1)}
                </div>
                <div className="text-xxs text-text-muted">avg lands</div>
              </div>
              <div>
                <div className="text-lg font-bold text-accent-blue">
                  {(handHistory.reduce((sum, h) => sum + h.spells, 0) / totalHands).toFixed(1)}
                </div>
                <div className="text-xxs text-text-muted">avg spells</div>
              </div>
              <div>
                <div className="text-lg font-bold text-text-primary">{totalHands}</div>
                <div className="text-xxs text-text-muted">hands drawn</div>
              </div>
            </div>

            <div className="mt-3">
              <div className="text-xxs text-text-muted text-center mb-1">
                % of hands with N lands (2-4 is ideal)
              </div>
              <div className="flex gap-2 justify-center">
                {[0, 1, 2, 3, 4, 5, 6, 7].map((n) => {
                  const count = handHistory.filter((h) => h.lands === n).length;
                  const pct = ((count / totalHands) * 100).toFixed(0);
                  return (
                    <div key={n} className="text-center">
                      <div className={`text-xs font-medium ${
                        n >= 2 && n <= 4 ? "text-accent-green" : n === 0 || n >= 6 ? "text-accent-red" : "text-text-secondary"
                      }`}>
                        {pct}%
                      </div>
                      <div className="text-xxs text-text-muted">{n} lands</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
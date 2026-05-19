"use client";

import { useState, useEffect } from "react";
import { DeckCard } from "@/lib/types";

interface Props {
  deckId: string;
  cards: DeckCard[];
  onClose: () => void;
}

function CardInHand({ 
  name, 
  scryfallId, 
  selected, 
  onClick, 
  selectable 
}: { 
  name: string; 
  scryfallId: string; 
  selected?: boolean;
  onClick?: () => void;
  selectable?: boolean;
}) {
  const [imgError, setImgError] = useState(false);

  return (
    <div 
      className={`flex-shrink-0 relative cursor-pointer transition-all ${
        selected ? "ring-2 ring-accent-red opacity-50 scale-95" : selectable ? "hover:scale-105" : ""
      }`}
      onClick={onClick}
    >
      {!imgError ? (
        <img
          src={`https://api.scryfall.com/cards/${scryfallId}?format=image&version=normal`}
          alt={name}
          className="w-32 rounded shadow-lg"
          onError={() => setImgError(true)}
          loading="lazy"
        />
      ) : (
        <div className="w-32 h-44 rounded bg-bg-tertiary border border-border flex items-center justify-center p-2">
          <span className="text-xxs text-text-secondary text-center">{name}</span>
        </div>
      )}
      {selected && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-accent-red text-lg font-bold bg-black/60 px-2 py-1 rounded">bottom</span>
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
    if (card.board === "sideboard" || card.board === "commander") continue;
    for (let i = 0; i < card.quantity; i++) {
      pool.push(card);
    }
  }
  return pool;
}

type Phase = "drawn" | "bottoming" | "kept";

export default function HandSimulator({ deckId, cards, onClose }: Props) {
  const [hand, setHand] = useState<DeckCard[]>([]);
  const [mulliganCount, setMulliganCount] = useState(0);
  const [phase, setPhase] = useState<Phase>("drawn");
  const [bottomIndices, setBottomIndices] = useState<Set<number>>(new Set());
  const [handHistory, setHandHistory] = useState<{ lands: number; spells: number; mulligans: number }[]>([]);

  function drawHand() {
    const pool = buildPool(cards);
    const shuffled = shuffle(pool);
    setHand(shuffled.slice(0, 7));
    setPhase("drawn");
    setBottomIndices(new Set());
  }

  function mulligan() {
    const newCount = mulliganCount + 1;
    if (newCount >= 7) return;
    setMulliganCount(newCount);
    // London mulligan: always draw 7
    const pool = buildPool(cards);
    const shuffled = shuffle(pool);
    setHand(shuffled.slice(0, 7));
    setPhase("drawn");
    setBottomIndices(new Set());
  }

  function startBottoming() {
    if (mulliganCount === 0) {
      // No mulligans, just keep
      keepHand();
      return;
    }
    setPhase("bottoming");
    setBottomIndices(new Set());
  }

  function toggleBottom(index: number) {
    setBottomIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else if (next.size < mulliganCount) {
        next.add(index);
      }
      return next;
    });
  }

  function confirmBottom() {
    const kept = hand.filter((_, i) => !bottomIndices.has(i));
    setHand(kept);
    setBottomIndices(new Set());
    setPhase("kept");
  }

  function keepHand() {
    const finalHand = phase === "kept" ? hand : hand;
    const lands = finalHand.filter(isLand).length;
    const spells = finalHand.length - lands;
    setHandHistory((prev) => [...prev, { lands, spells, mulligans: mulliganCount }]);
    setMulliganCount(0);
    setPhase("drawn");
    setBottomIndices(new Set());
    drawHand();
  }

  useEffect(() => {
    drawHand();
  }, []);

  const landCount = hand.filter(isLand).length;
  const spellCount = hand.length - landCount;
  const totalHands = handHistory.length;
  const commanderCard = cards.find((c) => c.board === "commander");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="panel p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-xs text-text-muted font-medium uppercase tracking-wider">
              Opening Hand Simulator
            </div>
            {mulliganCount > 0 && phase === "drawn" && (
              <div className="text-xxs text-accent-yellow mt-0.5">
                mulligan #{mulliganCount} — draw 7, then put {mulliganCount} on bottom
              </div>
            )}
            {phase === "bottoming" && (
              <div className="text-xxs text-accent-yellow mt-0.5">
                select {mulliganCount} card{mulliganCount !== 1 ? "s" : ""} to put on bottom ({bottomIndices.size}/{mulliganCount} selected)
              </div>
            )}
            {phase === "kept" && (
              <div className="text-xxs text-accent-green mt-0.5">
                keeping {hand.length} cards
              </div>
            )}
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            ✕
          </button>
        </div>

        {/* Commander in command zone */}
        {commanderCard && (
          <div className="text-center mb-2">
            <span className="text-xxs text-accent-purple">commander: {commanderCard.card_name} (command zone)</span>
          </div>
        )}

        <div className="flex gap-2 overflow-x-auto pb-4 px-4" style={{ justifyContent: hand.length <= 5 ? "center" : "flex-start" }}>
          {hand.map((card, i) => (
            <CardInHand
              key={`${card.scryfall_id}-${i}`}
              name={card.card_name}
              scryfallId={card.scryfall_id}
              selected={bottomIndices.has(i)}
              selectable={phase === "bottoming"}
              onClick={phase === "bottoming" ? () => toggleBottom(i) : undefined}
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
            {hand.length} cards
          </div>
        </div>

        <div className="flex gap-3 justify-center mb-4">
          {phase === "drawn" && (
            <>
              {mulliganCount < 6 && (
                <button
                  onClick={mulligan}
                  className="btn-danger"
                >
                  mulligan (draw 7 again)
                </button>
              )}
              <button onClick={startBottoming} className="btn-primary">
                {mulliganCount > 0 ? `keep — select ${mulliganCount} to bottom` : "keep — draw new hand"}
              </button>
            </>
          )}
          {phase === "bottoming" && (
            <>
              <button onClick={() => { setPhase("drawn"); setBottomIndices(new Set()); }} className="btn-ghost">
                ← back
              </button>
              <button
                onClick={confirmBottom}
                disabled={bottomIndices.size !== mulliganCount}
                className="btn-primary"
              >
                put {mulliganCount} on bottom
              </button>
            </>
          )}
          {phase === "kept" && (
            <button onClick={keepHand} className="btn-primary">
              done — draw new hand
            </button>
          )}
        </div>

        {totalHands > 0 && (
          <div className="border-t border-border pt-4">
            <div className="text-xxs text-text-muted font-medium uppercase tracking-wider mb-2">
              Session Stats ({totalHands} hand{totalHands !== 1 ? "s" : ""} kept)
            </div>
            <div className="grid grid-cols-4 gap-4 text-center">
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
                <div className="text-lg font-bold text-accent-yellow">
                  {(handHistory.reduce((sum, h) => sum + h.mulligans, 0) / totalHands).toFixed(1)}
                </div>
                <div className="text-xxs text-text-muted">avg mulligans</div>
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
"use client";

import { useState, useEffect } from "react";
import { ScryfallCard, DeckCard } from "@/lib/types";

function CardImage({ scryfallId }: { scryfallId: string }) {
  const [error, setError] = useState(false);

  if (error) return null;

  return (
    <img
      src={`https://api.scryfall.com/cards/${scryfallId}?format=image&version=normal`}
      alt=""
      className="w-56 rounded shadow-lg"
      onError={() => setError(true)}
      loading="lazy"
    />
  );
}

function ScoreBadge({ score }: { score: number }) {
  let color = "text-text-muted bg-bg-tertiary";
  let label = "—";

  if (score >= 9) {
    color = "text-accent-green bg-accent-green/10 border border-accent-green/30";
    label = "core";
  } else if (score >= 7) {
    color = "text-accent-blue bg-accent-blue/10 border border-accent-blue/30";
    label = "strong";
  } else if (score >= 5) {
    color = "text-accent-yellow bg-accent-yellow/10 border border-accent-yellow/30";
    label = "solid";
  } else {
    color = "text-accent-red bg-accent-red/10 border border-accent-red/30";
    label = "cuttable";
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {score}/10 — {label}
    </span>
  );
}

interface Props {
  cardData: ScryfallCard;
  deckCard: DeckCard;
  onUpdateNotes: (cardId: string, notes: string) => void;
}

export default function CardDetail({ cardData, deckCard, onUpdateNotes }: Props) {
  const [notes, setNotes] = useState(deckCard.notes || "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const aiContext = deckCard.ai_context;

  // Reset local state when deckCard changes
  useEffect(() => {
    setNotes(deckCard.notes || "");
  }, [deckCard.notes]);

  async function handleSaveNotes() {
    setSaving(true);
    onUpdateNotes(deckCard.id, notes);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Card image */}
        <div>
          <CardImage scryfallId={cardData.id} />
        </div>

        {/* Card info */}
        <div className="space-y-3 text-sm">
          {/* Type line */}
          <div>
            <span className="text-xxs text-text-muted uppercase tracking-wider">
              type
            </span>
            <p className="text-text-primary">{cardData.type_line}</p>
          </div>

          {/* Oracle text */}
          {cardData.oracle_text && (
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">
                text
              </span>
              <p className="text-text-secondary text-xs leading-relaxed whitespace-pre-line">
                {cardData.oracle_text}
              </p>
            </div>
          )}

          {/* Power / Toughness */}
          {cardData.power && cardData.toughness && (
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">
                p/t
              </span>
              <p className="text-text-primary">
                {cardData.power}/{cardData.toughness}
              </p>
            </div>
          )}

          {/* Set + Rarity */}
          <div className="flex gap-4">
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">
                set
              </span>
              <p className="text-text-secondary text-xs">{cardData.set_name}</p>
            </div>
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">
                rarity
              </span>
              <p className="text-text-secondary text-xs">{cardData.rarity}</p>
            </div>
          </div>

          {/* Price */}
          {cardData.prices?.usd && (
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">
                price
              </span>
              <p className="text-accent-green text-xs">
                ${cardData.prices.usd}
                {cardData.prices.usd_foil && (
                  <span className="text-text-muted ml-2">
                    foil: ${cardData.prices.usd_foil}
                  </span>
                )}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* AI Context section */}
      {aiContext && (
        <div className="border-t border-border pt-3">
          <div className="text-xxs text-text-muted uppercase tracking-wider mb-2">
            AI Analysis
          </div>

          <div className="space-y-2">
            {/* Impact score */}
            {aiContext.impact_score && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-secondary">impact:</span>
                <ScoreBadge score={aiContext.impact_score} />
                {aiContext.is_critical && (
                  <span className="text-xxs text-accent-green bg-accent-green/10 px-1.5 py-0.5 rounded border border-accent-green/30">
                    critical
                  </span>
                )}
              </div>
            )}

            {/* Role */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-text-secondary">role:</span>
              <span className="text-xs text-text-primary bg-bg-tertiary px-1.5 py-0.5 rounded">
                {aiContext.role}
              </span>
              {aiContext.secondary_roles?.map((role) => (
                <span
                  key={role}
                  className="text-xxs text-text-muted bg-bg-tertiary px-1.5 py-0.5 rounded"
                >
                  {role}
                </span>
              ))}
            </div>

            {/* Impact reason */}
            {aiContext.impact_reason && (
              <div>
                <span className="text-xs text-text-secondary">assessment: </span>
                <span className="text-xs text-text-primary">
                  {aiContext.impact_reason}
                </span>
              </div>
            )}

            {/* Synergy notes */}
            {aiContext.synergy_notes && (
              <div>
                <span className="text-xs text-text-secondary">synergy: </span>
                <span className="text-xs text-text-primary">
                  {aiContext.synergy_notes}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* User notes section */}
      <div className="border-t border-border pt-3">
        <div className="text-xxs text-text-muted uppercase tracking-wider mb-2">
          Your Notes
        </div>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="input-terminal text-xs min-h-[60px] resize-y w-full"
          placeholder="Add notes about this card... (strategy thoughts, combo pieces, upgrade plans)"
        />
        <div className="flex items-center gap-2 mt-2">
          <button
            onClick={handleSaveNotes}
            disabled={saving || notes === (deckCard.notes || "")}
            className="btn-primary text-xs px-3 py-1"
          >
            {saving ? "saving..." : "save notes"}
          </button>
          {saved && (
            <span className="text-accent-green text-xs">saved</span>
          )}
        </div>
      </div>
    </div>
  );
}
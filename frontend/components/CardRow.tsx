"use client";

import { useState } from "react";
import { DeckCard, ScryfallCard } from "@/lib/types";
import ManaCost from "./ManaCost";
import CardDetail from "./CardDetail";

interface Props {
  card: DeckCard;
  cardData?: ScryfallCard;
  onUpdateQuantity: (cardId: string, quantity: number) => void;
  onRemoveCard: (cardId: string) => void;
  onUpdateNotes: (cardId: string, notes: string) => void;
  format: string;
}

export default function CardRow({
  card,
  cardData,
  onUpdateQuantity,
  onRemoveCard,
  onUpdateNotes,
  format,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const isSingleton = format === "commander";
  const aiContext = card.ai_context;

  return (
    <div className="group">
      <div className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-bg-hover transition-colors">
        {/* Quantity controls */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => {
              if (card.quantity > 1) {
                onUpdateQuantity(card.id, card.quantity - 1);
              }
            }}
            disabled={card.quantity <= 1}
            className="w-5 h-5 flex items-center justify-center text-xs text-text-muted hover:text-text-primary disabled:opacity-30 transition-colors"
          >
            −
          </button>
          <span className="w-5 text-center text-xs text-text-secondary">
            {card.quantity}
          </span>
          <button
            onClick={() => {
              if (!isSingleton || card.board === "main") {
                onUpdateQuantity(card.id, card.quantity + 1);
              }
            }}
            disabled={isSingleton && card.board !== "main"}
            className="w-5 h-5 flex items-center justify-center text-xs text-text-muted hover:text-text-primary disabled:opacity-30 transition-colors"
          >
            +
          </button>
        </div>

        {/* Card name */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex-1 text-left text-sm text-text-primary hover:text-accent-green transition-colors truncate"
        >
          {card.card_name}
        </button>

        {/* Role name */}
        {aiContext?.role && (
          <span className="text-xxs text-text-muted flex-shrink-0">
            {aiContext.role}
          </span>
        )}

        {/* Notes indicator */}
        {card.notes && (
          <span className="text-xxs text-accent-yellow flex-shrink-0" title="Has notes">
            ✎
          </span>
        )}

        {/* Mana cost */}
        {cardData && <ManaCost cost={cardData.mana_cost} />}

        {/* Remove */}
        <button
          onClick={() => onRemoveCard(card.id)}
          className="text-text-muted hover:text-accent-red text-xs opacity-0 group-hover:opacity-100 transition-all flex-shrink-0 ml-1"
        >
          ✕
        </button>
      </div>

      {/* Expanded detail */}
      {expanded && cardData && (
        <div className="ml-12 mr-2 mb-3 mt-1 p-3 bg-bg-primary rounded border border-border">
          <CardDetail
            cardData={cardData}
            deckCard={card}
            onUpdateNotes={onUpdateNotes}
          />
        </div>
      )}
      {expanded && !cardData && (
        <div className="ml-12 mr-2 mb-2 text-text-muted text-xs">
          loading card data...
        </div>
      )}
    </div>
  );
}
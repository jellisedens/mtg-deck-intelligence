"use client";

import { useState } from "react";
import { DeckCard, ScryfallCard } from "@/lib/types";
import CardRow from "./CardRow";

const TYPE_ORDER = [
  "Commander",
  "Creature",
  "Planeswalker",
  "Instant",
  "Sorcery",
  "Enchantment",
  "Artifact",
  "Land",
  "Other",
];

function getCardType(card: DeckCard, cardData?: ScryfallCard): string {
  if (card.board === "commander") return "Commander";
  const typeLine = cardData?.type_line?.toLowerCase() || "";
  if (typeLine.includes("creature")) return "Creature";
  if (typeLine.includes("planeswalker")) return "Planeswalker";
  if (typeLine.includes("instant")) return "Instant";
  if (typeLine.includes("sorcery")) return "Sorcery";
  if (typeLine.includes("enchantment")) return "Enchantment";
  if (typeLine.includes("artifact")) return "Artifact";
  if (typeLine.includes("land")) return "Land";
  return "Other";
}

type SortMode = "type" | "name" | "cmc" | "price" | "impact";

function sortCards(cards: DeckCard[], cardDataMap: Record<string, ScryfallCard>, mode: SortMode): DeckCard[] {
  const sorted = [...cards];
  switch (mode) {
    case "name":
      return sorted.sort((a, b) => a.card_name.localeCompare(b.card_name));
    case "cmc":
      return sorted.sort((a, b) => {
        const cmcA = cardDataMap[a.scryfall_id]?.cmc ?? 99;
        const cmcB = cardDataMap[b.scryfall_id]?.cmc ?? 99;
        return cmcA - cmcB || a.card_name.localeCompare(b.card_name);
      });
    case "price":
      return sorted.sort((a, b) => {
        const priceA = parseFloat(cardDataMap[a.scryfall_id]?.prices?.usd || "0");
        const priceB = parseFloat(cardDataMap[b.scryfall_id]?.prices?.usd || "0");
        return priceB - priceA || a.card_name.localeCompare(b.card_name);
      });
    case "impact":
      return sorted.sort((a, b) => {
        const scoreA = a.ai_context?.impact_score ?? 0;
        const scoreB = b.ai_context?.impact_score ?? 0;
        return scoreB - scoreA || a.card_name.localeCompare(b.card_name);
      });
    default:
      return sorted.sort((a, b) => a.card_name.localeCompare(b.card_name));
  }
}

interface Props {
  deckId: string;
  cards: DeckCard[];
  cardDataMap: Record<string, ScryfallCard>;
  onUpdateQuantity: (cardId: string, quantity: number) => Promise<string | null>;
  onRemoveCard: (cardId: string) => void;
  onChangeBoard: (cardId: string, board: string) => void;
  onUpdateNotes: (cardId: string, notes: string) => void;
  onRolesUpdated?: () => void;
  format: string;
}

export default function DeckList({
  deckId,
  cards,
  cardDataMap,
  onUpdateQuantity,
  onRemoveCard,
  onChangeBoard,
  onUpdateNotes,
  onRolesUpdated,
  format,
}: Props) {
  const [sortMode, setSortMode] = useState<SortMode>("type");
  const totalCards = cards.reduce((sum, c) => sum + c.quantity, 0);

  if (cards.length === 0) {
    return (
      <div className="panel p-6 text-center">
        <p className="text-text-secondary text-sm mb-1">no cards yet</p>
        <p className="text-text-muted text-xs">
          use the search bar above to add cards
        </p>
      </div>
    );
  }

  const boards = [
    { key: "commander", label: "commander" },
    { key: "main", label: "main" },
    { key: "sideboard", label: "sideboard" },
  ];

  const sortOptions: { key: SortMode; label: string }[] = [
    { key: "type", label: "type" },
    { key: "name", label: "name" },
    { key: "cmc", label: "cmc" },
    { key: "price", label: "price" },
  ];

  function renderCards(boardCards: DeckCard[]) {
    if (sortMode === "type") {
      // Group by type
      const typeGroups: Record<string, DeckCard[]> = {};
      boardCards.forEach((card) => {
        const cardData = cardDataMap[card.scryfall_id];
        const type = getCardType(card, cardData);
        if (!typeGroups[type]) typeGroups[type] = [];
        typeGroups[type].push(card);
      });

      const sortedTypes = TYPE_ORDER.filter(
        (t) => typeGroups[t] && typeGroups[t].length > 0
      );

      return sortedTypes.map((type) => {
        const typeCards = typeGroups[type];
        const typeCount = typeCards.reduce((sum, c) => sum + c.quantity, 0);

        return (
          <div key={type} className="mb-2 last:mb-0">
            <div className="flex items-center gap-2 px-2 py-0.5">
              <span className="text-xxs text-text-muted tracking-wider">{type}</span>
              <span className="text-xxs text-text-muted">({typeCount})</span>
              <div className="flex-1 h-px bg-border/50" />
            </div>
            {typeCards
              .sort((a, b) => a.card_name.localeCompare(b.card_name))
              .map((card) => (
                <CardRow
                  key={card.id}
                  card={card}
                  cardData={cardDataMap[card.scryfall_id]}
                  deckId={deckId}
                  onUpdateQuantity={onUpdateQuantity}
                  onRemoveCard={onRemoveCard}
                  onUpdateNotes={onUpdateNotes}
                  onRolesUpdated={onRolesUpdated}
                  format={format}
                  sortMode={sortMode}
                />
              ))}
          </div>
        );
      });
    }

    // Flat sorted list for non-type sorts
    const sorted = sortCards(boardCards, cardDataMap, sortMode);
    return sorted.map((card) => (
      <CardRow
        key={card.id}
        card={card}
        cardData={cardDataMap[card.scryfall_id]}
        deckId={deckId}
        onUpdateQuantity={onUpdateQuantity}
        onRemoveCard={onRemoveCard}
        onUpdateNotes={onUpdateNotes}
        onRolesUpdated={onRolesUpdated}
        format={format}
        sortMode={sortMode}
      />
    ));
  }

  return (
    <div className="panel">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <span className="text-xs text-text-muted font-medium uppercase tracking-wider">
          Deck List
        </span>
        <div className="flex items-center gap-3">
          <div className="flex gap-0.5 bg-bg-primary rounded p-0.5">
            {sortOptions.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setSortMode(opt.key)}
                className={`px-1.5 py-0.5 text-xxs rounded transition-colors ${
                  sortMode === opt.key
                    ? "bg-bg-tertiary text-text-primary"
                    : "text-text-muted hover:text-text-secondary"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <span className="text-xs text-text-secondary">
            {totalCards} card{totalCards !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <div className="p-2">
        {boards.map((board) => {
          const boardCards = cards.filter((c) => c.board === board.key);
          if (boardCards.length === 0) return null;

          const boardCount = boardCards.reduce((sum, c) => sum + c.quantity, 0);

          return (
            <div key={board.key} className="mb-4 last:mb-0">
              <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
                <span className="text-xs text-accent-green font-medium uppercase tracking-wider">
                  {board.label}
                </span>
                <span className="text-xxs text-text-muted">({boardCount})</span>
                <div className="flex-1 h-px bg-border" />
              </div>
              {renderCards(boardCards)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
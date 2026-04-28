"use client";

import { DeckCard, ScryfallCard } from "@/lib/types";
import CardRow from "./CardRow";

// ── Type categorization ──────────────────────────────
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

// ── Main component ───────────────────────────────────
interface Props {
  cards: DeckCard[];
  cardDataMap: Record<string, ScryfallCard>;
  onUpdateQuantity: (cardId: string, quantity: number) => void;
  onRemoveCard: (cardId: string) => void;
  onChangeBoard: (cardId: string, board: string) => void;
  format: string;
}

export default function DeckList({
  cards,
  cardDataMap,
  onUpdateQuantity,
  onRemoveCard,
  onChangeBoard,
  format,
}: Props) {
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

  return (
    <div className="panel">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <span className="text-xs text-text-muted font-medium uppercase tracking-wider">
          Deck List
        </span>
        <span className="text-xs text-text-secondary">
          {totalCards} card{totalCards !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Board sections */}
      <div className="p-2">
        {boards.map((board) => {
          const boardCards = cards.filter((c) => c.board === board.key);
          if (boardCards.length === 0) return null;

          const boardCount = boardCards.reduce(
            (sum, c) => sum + c.quantity,
            0
          );

          // Group by card type within this board
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

          return (
            <div key={board.key} className="mb-4 last:mb-0">
              {/* Board header */}
              <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
                <span className="text-xs text-accent-green font-medium uppercase tracking-wider">
                  {board.label}
                </span>
                <span className="text-xxs text-text-muted">
                  ({boardCount})
                </span>
                <div className="flex-1 h-px bg-border" />
              </div>

              {/* Type sub-groups */}
              {sortedTypes.map((type) => {
                const typeCards = typeGroups[type];
                const typeCount = typeCards.reduce(
                  (sum, c) => sum + c.quantity,
                  0
                );

                return (
                  <div key={type} className="mb-2 last:mb-0">
                    <div className="flex items-center gap-2 px-2 py-0.5">
                      <span className="text-xxs text-text-muted tracking-wider">
                        {type}
                      </span>
                      <span className="text-xxs text-text-muted">
                        ({typeCount})
                      </span>
                      <div className="flex-1 h-px bg-border/50" />
                    </div>

                    {typeCards
                      .sort((a, b) => a.card_name.localeCompare(b.card_name))
                      .map((card) => (
                        <CardRow
                          key={card.id}
                          card={card}
                          cardData={cardDataMap[card.scryfall_id]}
                          onUpdateQuantity={onUpdateQuantity}
                          onRemoveCard={onRemoveCard}
                          format={format}
                        />
                      ))}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
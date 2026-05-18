"use client";

import { useState } from "react";
import { DeckCard, ScryfallCard } from "@/lib/types";

interface Props {
  deckName: string;
  cards: DeckCard[];
  cardDataMap: Record<string, ScryfallCard>;
  onClose: () => void;
}

type ExportFormat = "text" | "mtgo";

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

const TYPE_ORDER = ["Commander", "Creature", "Planeswalker", "Instant", "Sorcery", "Enchantment", "Artifact", "Land", "Other"];

function buildExportText(cards: DeckCard[], cardDataMap: Record<string, ScryfallCard>, format: ExportFormat): string {
  const mainCards = cards.filter((c) => c.board === "main" || c.board === "commander");
  const sideboardCards = cards.filter((c) => c.board === "sideboard");

  const grouped: Record<string, DeckCard[]> = {};
  for (const card of mainCards) {
    const cardData = cardDataMap[card.scryfall_id];
    const type = getCardType(card, cardData);
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(card);
  }

  const lines: string[] = [];

  for (const type of TYPE_ORDER) {
    const group = grouped[type];
    if (!group || group.length === 0) continue;

    lines.push(`// ${type} (${group.reduce((s, c) => s + c.quantity, 0)})`);
    group.sort((a, b) => a.card_name.localeCompare(b.card_name));
    for (const card of group) {
      if (format === "text") {
        lines.push(`${card.quantity}x ${card.card_name}`);
      } else {
        lines.push(`${card.quantity} ${card.card_name}`);
      }
    }
    lines.push("");
  }

  if (sideboardCards.length > 0) {
    lines.push("// Sideboard");
    sideboardCards.sort((a, b) => a.card_name.localeCompare(b.card_name));
    for (const card of sideboardCards) {
      if (format === "text") {
        lines.push(`${card.quantity}x ${card.card_name}`);
      } else {
        lines.push(`${card.quantity} ${card.card_name}`);
      }
    }
  }

  return lines.join("\n").trim();
}

export default function ExportDeckModal({ deckName, cards, cardDataMap, onClose }: Props) {
  const [format, setFormat] = useState<ExportFormat>("text");
  const [copied, setCopied] = useState(false);

  const exportText = buildExportText(cards, cardDataMap, format);
  const totalCards = cards.reduce((s, c) => s + c.quantity, 0);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(exportText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className="w-full max-w-lg bg-bg-secondary border border-border rounded-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div>
            <h2 className="text-sm font-bold text-text-primary">export deck</h2>
            <p className="text-xxs text-text-muted mt-0.5">{deckName} — {totalCards} cards</p>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">✕</button>
        </div>

        <div className="p-4">
          <div className="flex gap-1 bg-bg-primary rounded p-0.5 mb-3">
            {([
              { key: "text" as ExportFormat, label: "text (1x)" },
              { key: "mtgo" as ExportFormat, label: "MTGO" },
            ]).map((f) => (
              <button
                key={f.key}
                onClick={() => setFormat(f.key)}
                className={`flex-1 px-2 py-1.5 text-xs rounded transition-colors ${
                  format === f.key
                    ? "bg-bg-tertiary text-text-primary"
                    : "text-text-muted hover:text-text-secondary"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <textarea
            readOnly
            value={exportText}
            className="input-terminal min-h-[300px] resize-y font-mono text-xs"
          />

          <div className="flex justify-end gap-2 mt-3">
            <button onClick={onClose} className="btn-ghost text-xs">close</button>
            <button onClick={handleCopy} className="btn-primary text-xs">
              {copied ? "✓ copied!" : "copy to clipboard"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
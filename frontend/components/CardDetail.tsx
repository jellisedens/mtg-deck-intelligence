"use client";

import { useState } from "react";
import { ScryfallCard } from "@/lib/types";

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

interface Props {
  cardData: ScryfallCard;
}

export default function CardDetail({ cardData }: Props) {
  return (
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
  );
}
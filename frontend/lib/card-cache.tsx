"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { getCardCollection } from "./api";
import { ScryfallCard } from "./types";

interface CardCacheContextType {
  cardDataMap: Record<string, ScryfallCard>;
  fetchCards: (scryfallIds: string[]) => Promise<void>;
  addCard: (card: ScryfallCard) => void;
  isLoading: boolean;
}

const CardCacheContext = createContext<CardCacheContextType>({
  cardDataMap: {},
  fetchCards: async () => {},
  addCard: () => {},
  isLoading: false,
});

export function CardCacheProvider({ children }: { children: ReactNode }) {
  const [cardDataMap, setCardDataMap] = useState<Record<string, ScryfallCard>>({});
  const [isLoading, setIsLoading] = useState(false);

  const fetchCards = useCallback(
    async (scryfallIds: string[]) => {
      // Filter out IDs we already have cached
      const needed = scryfallIds.filter((id) => !cardDataMap[id]);

      if (needed.length === 0) return;

      setIsLoading(true);

      try {
        const cards = await getCardCollection(needed);
        const newData: Record<string, ScryfallCard> = {};

        cards.forEach((card) => {
          newData[card.id] = card;
        });

        setCardDataMap((prev) => ({ ...prev, ...newData }));
      } catch (err) {
        console.error("Failed to fetch card collection:", err);
      } finally {
        setIsLoading(false);
      }
    },
    [cardDataMap]
  );

  // Add a single card to cache (used when adding a card via search)
  const addCard = useCallback((card: ScryfallCard) => {
    setCardDataMap((prev) => ({ ...prev, [card.id]: card }));
  }, []);

  return (
    <CardCacheContext.Provider
      value={{ cardDataMap, fetchCards, addCard, isLoading }}
    >
      {children}
    </CardCacheContext.Provider>
  );
}

export function useCardCache() {
  return useContext(CardCacheContext);
}
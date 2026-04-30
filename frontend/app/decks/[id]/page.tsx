"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import CardSearch from "@/components/CardSearch";
import DeckList from "@/components/DeckList";
import DeckAnalytics from "@/components/DeckAnalytics";
import HandSimulator from "@/components/HandSimulator";
import { getDeck, addCard, updateCard, removeCard } from "@/lib/api";
import { useCardCache } from "@/lib/card-cache";
import { Deck, ScryfallCard } from "@/lib/types";

function DeckBuilderContent({ deckId }: { deckId: string }) {
  const router = useRouter();

  const [deck, setDeck] = useState<Deck | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [showHandSim, setShowHandSim] = useState(false);

  const { cardDataMap, fetchCards, addCard: cacheCard, isLoading: cardsLoading } = useCardCache();

  async function loadDeck() {
    try {
      const data = await getDeck(deckId);
      setDeck(data);

      if (data.cards && data.cards.length > 0) {
        const ids = data.cards.map((c) => c.scryfall_id);
        await fetchCards(ids);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load deck");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDeck();
  }, [deckId]);

  async function handleAddCard(card: ScryfallCard) {
    if (!deck) return;
    setActionError("");

    const isCommander =
      deck.format === "commander" &&
      card.type_line?.toLowerCase().includes("legendary") &&
      card.type_line?.toLowerCase().includes("creature") &&
      (!deck.cards || !deck.cards.some((c) => c.board === "commander"));

    try {
      const updated = await addCard(deckId, {
        scryfall_id: card.id,
        card_name: card.name,
        quantity: 1,
        board: isCommander ? "commander" : "main",
      });
      setDeck(updated);
      cacheCard(card);
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to add card"
      );
    }
  }

  async function handleUpdateQuantity(cardId: string, quantity: number) {
    setActionError("");
    try {
      const updated = await updateCard(deckId, cardId, { quantity });
      setDeck(updated);
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to update card"
      );
    }
  }

  async function handleRemoveCard(cardId: string) {
    if (!deck) return;
    setActionError("");
    try {
      await removeCard(deckId, cardId);
      setDeck({
        ...deck,
        cards: deck.cards?.filter((c) => c.id !== cardId),
      });
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to remove card"
      );
    }
  }

  async function handleChangeBoard(cardId: string, board: string) {
    setActionError("");
    try {
      const updated = await updateCard(deckId, cardId, { board });
      setDeck(updated);
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to move card"
      );
    }
  }

  async function handleUpdateNotes(cardId: string, notes: string) {
    setActionError("");
    try {
      const updated = await updateCard(deckId, cardId, { notes });
      setDeck(updated);
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to save notes"
      );
    }
  }

  if (loading) {
    return (
      <div className="text-text-muted text-sm">
        <span className="text-accent-green">$</span> loading deck...
        <span className="animate-pulse">█</span>
      </div>
    );
  }

  if (error || !deck) {
    return (
      <div>
        <div className="text-accent-red text-sm mb-4">
          error: {error || "Deck not found"}
        </div>
        <button onClick={() => router.push("/decks")} className="btn-ghost">
          ← back to decks
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push("/decks")}
              className="text-text-muted hover:text-text-primary transition-colors text-sm"
            >
              ~/decks
            </button>
            <span className="text-text-muted">/</span>
            <h1 className="text-lg font-bold text-text-primary">
              {deck.name}
            </h1>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="px-1.5 py-0.5 text-xxs rounded bg-bg-tertiary text-text-secondary">
              {deck.format}
            </span>
            {deck.description && (
              <span className="text-xs text-text-muted">
                {deck.description}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => setShowHandSim(true)}
          className="btn-primary text-xs"
        >
          draw hand
        </button>
      </div>

      {actionError && (
        <div className="mb-4 px-3 py-2 bg-accent-red/10 border border-accent-red/30 rounded text-accent-red text-sm">
          {actionError}
          <button
            onClick={() => setActionError("")}
            className="ml-2 text-accent-red/60 hover:text-accent-red"
          >
            ✕
          </button>
        </div>
      )}

      {cardsLoading && (
        <div className="mb-4 text-text-muted text-xs">
          <span className="text-accent-green">$</span> fetching card data...
          <span className="animate-pulse">█</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <CardSearch onAddCard={handleAddCard} />
          <DeckList
            cards={deck.cards || []}
            cardDataMap={cardDataMap}
            onUpdateQuantity={handleUpdateQuantity}
            onRemoveCard={handleRemoveCard}
            onChangeBoard={handleChangeBoard}
            onUpdateNotes={handleUpdateNotes}
            format={deck.format}
          />
        </div>

        <div className="space-y-4">
          <DeckAnalytics
            deckId={deckId}
            cardCount={deck.cards?.reduce((sum, c) => sum + c.quantity, 0) || 0}
          />
        </div>
      </div>

      {showHandSim && (
        <HandSimulator
          deckId={deckId}
          onClose={() => setShowHandSim(false)}
        />
      )}
    </div>
  );
}

export default function DeckBuilderPage() {
  const [deckId, setDeckId] = useState<string | null>(null);

  useEffect(() => {
    const pathParts = window.location.pathname.split("/");
    const id = pathParts[pathParts.length - 1];
    if (id && id !== "decks") {
      setDeckId(id);
    }
  }, []);

  if (!deckId) {
    return (
      <ProtectedRoute>
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-text-muted text-sm">
            <span className="text-accent-green">$</span> loading...
            <span className="animate-pulse">█</span>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="max-w-7xl mx-auto px-4 py-8">
        <DeckBuilderContent deckId={deckId} />
      </div>
    </ProtectedRoute>
  );
}
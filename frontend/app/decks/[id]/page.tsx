"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import CardSearch from "@/components/CardSearch";
import DeckList from "@/components/DeckList";
import DeckAnalytics from "@/components/DeckAnalytics";
import HandSimulator from "@/components/HandSimulator";
import GameSimulator from "@/components/GameSimulator";
import AISuggestPanel from "@/components/AISuggestPanel";
import DeckPreferences from "@/components/DeckPreferences";
import StrategyGenerator from "@/components/StrategyGenerator";
import { getDeck, addCard, updateCard, removeCard, getStrategy } from "@/lib/api";
import { useCardCache } from "@/lib/card-cache";
import { Deck, ScryfallCard } from "@/lib/types";
import { usePathname } from "next/navigation";
import DeckVersions from "@/components/DeckVersions";
import VerificationBanner from "@/components/VerificationBanner";

function DeckBuilderContent({ deckId }: { deckId: string }) {
  const router = useRouter();
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

  const [deck, setDeck] = useState<Deck | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [showHandSim, setShowHandSim] = useState(false);
  const [showGameSim, setShowGameSim] = useState(false);
  const [hasStrategy, setHasStrategy] = useState(false);
  const [strategy, setStrategy] = useState<Record<string, unknown> | null>(null);

  const { cardDataMap, fetchCards, addCard: cacheCard, isLoading: cardsLoading } = useCardCache();

  async function loadDeck() {
    try {
      const data = await getDeck(deckId);
      setDeck(data);

      const strat = await getStrategy(deckId);
      setStrategy(strat);
      setHasStrategy(!!strat);

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
      await addCard(deckId, {
        scryfall_id: card.id,
        card_name: card.name,
        quantity: 1,
        board: isCommander ? "commander" : "main",
      });
      const refreshed = await getDeck(deckId);
      setDeck(refreshed);
      cacheCard(card);
      } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to add card"
      );
    }
  }

  async function handleAddCardById(scryfallId: string, cardName: string) {
    if (!deck) return;
    setActionError("");
    try {
      const res = await fetch(`${API_BASE}/decks/${deckId}/cards`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("mtg_token")}`,
        },
        body: JSON.stringify({
          scryfall_id: scryfallId,
          card_name: cardName,
          quantity: 1,
          board: "main",
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Failed: ${res.status}`);
      }
      const refreshed = await getDeck(deckId);
      setDeck(refreshed);
      await fetchCards([scryfallId]);
      } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to add card"
      );
      throw err;
    }
  }

  async function handleUpdateQuantity(cardId: string, quantity: number): Promise<string | null> {
    setActionError("");
    try {
      await updateCard(deckId, cardId, { quantity });
      const refreshed = await getDeck(deckId);
      setDeck(refreshed);
      return null;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update card";
      return msg;
    }
  }

  async function handleRemoveCard(cardId: string) {
    if (!deck) return;
    setActionError("");
    try {
      await removeCard(deckId, cardId);
      const refreshed = await getDeck(deckId);
      setDeck(refreshed);
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to remove card"
      );
    }
  }

  async function handleChangeBoard(cardId: string, board: string) {
    setActionError("");
    try {
      await updateCard(deckId, cardId, { board });
      const refreshed = await getDeck(deckId);
      setDeck(refreshed);
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to move card"
      );
    }
  }

  async function handleUpdateNotes(cardId: string, notes: string) {
    setActionError("");
    try {
      await updateCard(deckId, cardId, { notes });
      const refreshed = await getDeck(deckId);
      setDeck(refreshed);
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to save notes"
      );
    }
  }

  async function handleAutoTagRoles() {
    if (!confirm(
      "Auto-tag will analyze all untagged cards and assign roles based on oracle text.\n\n" +
      "Cards you've already tagged will keep their current roles.\n\nProceed?"
    )) return;

    try {
      const token = localStorage.getItem("mtg_token");
      const res = await fetch(`${API_BASE}/decks/${deckId}/roles/auto-suggest`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.updated > 0) {
          setActionError("");
          await loadDeck();
          alert(`Auto-tagged ${data.updated} cards. ${data.skipped_tagged} already tagged.`);
        } else {
          alert("All cards already have roles assigned.");
        }
      }
    } catch {
      setActionError("Failed to auto-tag roles");
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
      <VerificationBanner />
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push("/decks")}
              className="text-text-muted hover:text-text-primary transition-colors text-sm flex-shrink-0"
            >
              ~/decks
            </button>
            <span className="text-text-muted">/</span>
            <h1 className="text-lg font-bold text-text-primary truncate">
              {deck.name}
            </h1>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="px-1.5 py-0.5 text-xxs rounded bg-bg-tertiary text-text-secondary flex-shrink-0">
              {deck.format}
            </span>
            {deck.description && (
              <span className="text-xs text-text-muted truncate">
                {deck.description}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setShowHandSim(true)}
            className="btn-primary text-xs"
          >
            draw hand
          </button>
          <button
            onClick={() => setShowGameSim(true)}
            className="btn-ghost text-xs"
          >
            simulate
          </button>
          <button
            onClick={handleAutoTagRoles}
            className="btn-ghost text-xs"
          >
            auto-tag
          </button>
        </div>
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
            deckId={deckId}
            cards={deck.cards || []}
            cardDataMap={cardDataMap}
            onUpdateQuantity={handleUpdateQuantity}
            onRemoveCard={handleRemoveCard}
            onChangeBoard={handleChangeBoard}
            onUpdateNotes={handleUpdateNotes}
            onRolesUpdated={() => loadDeck()}
            format={deck.format}
          />
        </div>

        <div className="space-y-4">
          <StrategyGenerator
            deckId={deckId}
            hasProfile={hasStrategy}
            onComplete={() => window.location.reload()}
            cardCount={deck.cards?.length || 0}
            strategy={strategy}
          />
          <DeckPreferences
            deckId={deckId}
            currentPreferences={deck.preferences as unknown as Record<string, string | null> | null}
            onSaved={() => loadDeck()}
          />
          <AISuggestPanel deckId={deckId} onAddCard={handleAddCardById} />
          <DeckVersions
            deckId={deckId}
            cardCount={deck.cards?.reduce((sum, c) => sum + c.quantity, 0) || 0}
          />
          <DeckAnalytics
            deckId={deckId}
            cardCount={deck.cards?.reduce((sum, c) => sum + c.quantity, 0) || 0}
            strategy={strategy}
          />
        </div>
      </div>

      {showHandSim && (
        <HandSimulator
          deckId={deckId}
          cards={deck.cards || []}
          onClose={() => setShowHandSim(false)}
        />
      )}

      {showGameSim && (
        <GameSimulator
          deckId={deckId}
          onClose={() => setShowGameSim(false)}
        />
      )}
    </div>
  );
}

export default function DeckBuilderPage() {
  const pathname = usePathname();
  const deckId = pathname?.split("/").pop() || null;

  if (!deckId || deckId === "decks") {
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
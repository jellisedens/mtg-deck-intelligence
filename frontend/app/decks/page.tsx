"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import CreateDeckModal from "@/components/CreateDeckModal";
import ImportDeckModal from "@/components/ImportDeckModal";
import { getDecks, deleteDeck } from "@/lib/api";
import { Deck } from "@/lib/types";

function DecksContent() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const router = useRouter();

  async function loadDecks() {
    try {
      const data = await getDecks();
      setDecks(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load decks");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDecks();
  }, []);

  async function handleDelete(deckId: string) {
    if (confirmDelete !== deckId) {
      setConfirmDelete(deckId);
      return;
    }

    try {
      await deleteDeck(deckId);
      setDecks((prev) => prev.filter((d) => d.id !== deckId));
      setConfirmDelete(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete deck");
    }
  }

  if (loading) {
    return (
      <div className="text-text-muted text-sm">
        <span className="text-accent-green">$</span> loading decks...
        <span className="animate-pulse">█</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-accent-red text-sm">
        error: {error}
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-text-primary">
            <span className="text-accent-green">~/</span>decks
          </h1>
          <p className="text-text-muted text-xs mt-1">
            {decks.length} deck{decks.length !== 1 ? "s" : ""} found
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowImport(true)}
            className="btn-ghost"
          >
            import
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary"
          >
            + new deck
          </button>
        </div>
      </div>

      {/* Deck list */}
      {decks.length === 0 ? (
        <div className="panel p-8 text-center">
          <p className="text-text-secondary text-sm mb-3">no decks yet</p>
          <p className="text-text-muted text-xs mb-4">
            create a new deck or import one to get started
          </p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={() => setShowImport(true)}
              className="btn-ghost"
            >
              import
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className="btn-primary"
            >
              + new deck
            </button>
          </div>
        </div>
      ) : (
        <div className="grid gap-2">
          {decks.map((deck) => (
            <div
              key={deck.id}
              className="panel p-4 hover:bg-bg-hover transition-colors cursor-pointer group"
              onClick={() => router.push(`/decks/${deck.id}`)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-medium text-text-primary truncate">
                      {deck.name}
                    </h2>
                    <span className="px-1.5 py-0.5 text-xxs rounded bg-bg-tertiary text-text-secondary flex-shrink-0">
                      {deck.format}
                    </span>
                  </div>
                  {deck.description && (
                    <p className="text-xs text-text-muted mt-0.5 truncate">
                      {deck.description}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-3 ml-4">
                  {deck.cards && (
                    <span className="text-xs text-text-muted">
                      {deck.cards.reduce((sum, c) => sum + c.quantity, 0)} cards
                    </span>
                  )}
                  <span className="text-xs text-text-muted">
                    {new Date(deck.updated_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(deck.id);
                    }}
                    className={`px-2 py-1 text-xs rounded transition-colors ${
                      confirmDelete === deck.id
                        ? "bg-accent-red/10 text-accent-red border border-accent-red/30"
                        : "text-text-muted hover:text-accent-red opacity-0 group-hover:opacity-100"
                    }`}
                  >
                    {confirmDelete === deck.id ? "confirm?" : "✕"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      {showCreate && (
        <CreateDeckModal
          onClose={() => setShowCreate(false)}
          onCreated={(deck) => {
            setDecks((prev) => [deck, ...prev]);
            setShowCreate(false);
            router.push(`/decks/${deck.id}`);
          }}
        />
      )}

      {showImport && (
        <ImportDeckModal
          onClose={() => setShowImport(false)}
          onImported={(deck) => {
            setDecks((prev) => [deck, ...prev]);
            setShowImport(false);
          }}
        />
      )}
    </div>
  );
}

export default function DecksPage() {
  return (
    <ProtectedRoute>
      <div className="max-w-4xl mx-auto px-4 py-8">
        <DecksContent />
      </div>
    </ProtectedRoute>
  );
}
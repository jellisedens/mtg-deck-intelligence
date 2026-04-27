"use client";

import { useState, FormEvent } from "react";
import { createDeck } from "@/lib/api";
import { Deck } from "@/lib/types";

const FORMATS = [
  "commander",
  "standard",
  "modern",
  "pioneer",
  "pauper",
  "legacy",
  "vintage",
];

interface Props {
  onClose: () => void;
  onCreated: (deck: Deck) => void;
}

export default function CreateDeckModal({ onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [format, setFormat] = useState("commander");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!name.trim()) {
      setError("Deck name is required");
      return;
    }

    setLoading(true);

    try {
      const deck = await createDeck({
        name: name.trim(),
        format,
        description: description.trim() || undefined,
      });
      onCreated(deck);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create deck");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="panel p-6 w-full max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="text-xs text-text-muted font-medium uppercase tracking-wider">
            New Deck
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mb-4 px-3 py-2 bg-accent-red/10 border border-accent-red/30 rounded text-accent-red text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-text-secondary mb-1.5">
              name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-terminal"
              placeholder="My Awesome Deck"
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs text-text-secondary mb-1.5">
              format
            </label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="input-terminal"
            >
              {FORMATS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-text-secondary mb-1.5">
              description{" "}
              <span className="text-text-muted">(optional)</span>
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input-terminal"
              placeholder="5-color dragon tribal"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-ghost flex-1"
            >
              cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex-1"
            >
              {loading ? (
                <span>
                  creating<span className="animate-pulse">...</span>
                </span>
              ) : (
                "create deck →"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
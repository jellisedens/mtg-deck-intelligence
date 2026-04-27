"use client";

import { useState, FormEvent } from "react";
import { importArchidekt, importText } from "@/lib/api";
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

type Tab = "archidekt" | "text";

interface Props {
  onClose: () => void;
  onImported: (deck: Deck) => void;
}

export default function ImportDeckModal({ onClose, onImported }: Props) {
  const [tab, setTab] = useState<Tab>("archidekt");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Archidekt fields
  const [url, setUrl] = useState("");

  // Text import fields
  const [textName, setTextName] = useState("");
  const [textFormat, setTextFormat] = useState("commander");
  const [textList, setTextList] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let deck: Deck;

      if (tab === "archidekt") {
        if (!url.trim()) {
          setError("URL is required");
          setLoading(false);
          return;
        }
        deck = await importArchidekt({ url: url.trim() });
      } else {
        if (!textName.trim()) {
          setError("Deck name is required");
          setLoading(false);
          return;
        }
        if (!textList.trim()) {
          setError("Deck list is required");
          setLoading(false);
          return;
        }
        deck = await importText({
          name: textName.trim(),
          format: textFormat,
          text: textList.trim(),
        });
      }

      onImported(deck);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Import failed");
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
        className="panel p-6 w-full max-w-lg mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="text-xs text-text-muted font-medium uppercase tracking-wider">
            Import Deck
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 p-1 bg-bg-primary rounded">
          <button
            onClick={() => { setTab("archidekt"); setError(""); }}
            className={`flex-1 px-3 py-1.5 text-sm rounded transition-colors ${
              tab === "archidekt"
                ? "bg-bg-tertiary text-text-primary"
                : "text-text-muted hover:text-text-secondary"
            }`}
          >
            archidekt
          </button>
          <button
            onClick={() => { setTab("text"); setError(""); }}
            className={`flex-1 px-3 py-1.5 text-sm rounded transition-colors ${
              tab === "text"
                ? "bg-bg-tertiary text-text-primary"
                : "text-text-muted hover:text-text-secondary"
            }`}
          >
            text list
          </button>
        </div>

        {error && (
          <div className="mb-4 px-3 py-2 bg-accent-red/10 border border-accent-red/30 rounded text-accent-red text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {tab === "archidekt" ? (
            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                archidekt url
              </label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="input-terminal"
                placeholder="https://archidekt.com/decks/..."
                required
                autoFocus
              />
              <p className="text-xxs text-text-muted mt-1.5">
                deck must be public on archidekt
              </p>
            </div>
          ) : (
            <>
              <div>
                <label className="block text-xs text-text-secondary mb-1.5">
                  deck name
                </label>
                <input
                  type="text"
                  value={textName}
                  onChange={(e) => setTextName(e.target.value)}
                  className="input-terminal"
                  placeholder="My Imported Deck"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-xs text-text-secondary mb-1.5">
                  format
                </label>
                <select
                  value={textFormat}
                  onChange={(e) => setTextFormat(e.target.value)}
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
                  deck list
                </label>
                <textarea
                  value={textList}
                  onChange={(e) => setTextList(e.target.value)}
                  className="input-terminal min-h-[200px] resize-y font-mono text-xs"
                  placeholder={`1 The Ur-Dragon\n4 Lightning Bolt\n2 Counterspell\n38 Mountain`}
                  required
                />
                <p className="text-xxs text-text-muted mt-1.5">
                  one card per line: quantity + card name
                </p>
              </div>
            </>
          )}

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
                  importing<span className="animate-pulse">...</span>
                </span>
              ) : (
                "import deck →"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
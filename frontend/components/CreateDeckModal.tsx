"use client";

import { useState, useEffect, FormEvent } from "react";
import { createDeck, autocompleteCards, searchCards, addCard, updateDeckPreferences } from "@/lib/api";
import { Deck, ScryfallCard } from "@/lib/types";

const FORMATS = [
  "commander",
  "standard",
  "modern",
  "pioneer",
  "pauper",
  "legacy",
  "vintage",
];

const POWER_LEVELS = [
  { value: "", label: "not set" },
  { value: "casual", label: "casual — fun first" },
  { value: "focused", label: "focused — has a plan" },
  { value: "optimized", label: "optimized — tuned and efficient" },
  { value: "cedh", label: "cEDH — competitive" },
];

interface Props {
  onClose: () => void;
  onCreated: (deck: Deck) => void;
}

export default function CreateDeckModal({ onClose, onCreated }: Props) {
  const [step, setStep] = useState<"basics" | "commander" | "preferences">("basics");

  // Step 1: Basics
  const [name, setName] = useState("");
  const [format, setFormat] = useState("commander");
  const [description, setDescription] = useState("");

  // Step 2: Commander
  const [commanderQuery, setCommanderQuery] = useState("");
  const [commanderSuggestions, setCommanderSuggestions] = useState<string[]>([]);
  const [commanderResults, setCommanderResults] = useState<ScryfallCard[]>([]);
  const [selectedCommander, setSelectedCommander] = useState<ScryfallCard | null>(null);
  const [searchingCommander, setSearchingCommander] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  // Step 3: Preferences
  const [powerLevel, setPowerLevel] = useState("");
  const [strategyNotes, setStrategyNotes] = useState("");
  const [budget, setBudget] = useState("");

  // Shared
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [createdDeck, setCreatedDeck] = useState<Deck | null>(null);

  // Commander autocomplete
  useEffect(() => {
    if (commanderQuery.length < 2) {
      setCommanderSuggestions([]);
      setShowDropdown(false);
      return;
    }
    const timeout = setTimeout(async () => {
      try {
        const results = await autocompleteCards(commanderQuery);
        setCommanderSuggestions(results);
        setShowDropdown(results.length > 0);
      } catch {
        setCommanderSuggestions([]);
      }
    }, 200);
    return () => clearTimeout(timeout);
  }, [commanderQuery]);

  async function handleSelectCommanderName(cardName: string) {
    setCommanderQuery(cardName);
    setShowDropdown(false);
    setSearchingCommander(true);
    try {
      // Search for the exact card to check if it's legendary
      const results = await searchCards(`!"${cardName}" t:legendary`);
      if (results.length > 0) {
        setSelectedCommander(results[0]);
        setCommanderResults([]);
      } else {
        // Not legendary — search without the type filter to show the card
        const allResults = await searchCards(`!"${cardName}"`);
        if (allResults.length > 0) {
          setError(`${cardName} is not a legendary creature. Choose a legendary creature as your commander.`);
          setSelectedCommander(null);
        } else {
          setError("Card not found.");
          setSelectedCommander(null);
        }
      }
    } catch {
      setError("Failed to search for card.");
    } finally {
      setSearchingCommander(false);
    }
  }

  async function handleBasicsSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!name.trim()) {
      setError("Deck name is required");
      return;
    }

    if (format === "commander") {
      setStep("commander");
    } else {
      // Non-commander formats skip straight to creation
      await createAndFinish();
    }
  }

  async function handleCommanderSubmit() {
    setError("");
    if (!selectedCommander) {
      setError("Please select a commander");
      return;
    }
    setStep("preferences");
  }

  async function handlePreferencesSubmit() {
    setError("");
    await createAndFinish();
  }

  async function createAndFinish() {
    setLoading(true);
    try {
      // Create the deck
      const deck = await createDeck({
        name: name.trim(),
        format,
        description: description.trim() || undefined,
      });

      // If commander format, add the commander card
      if (format === "commander" && selectedCommander) {
        await addCard(deck.id, {
          scryfall_id: selectedCommander.id,
          card_name: selectedCommander.name,
          quantity: 1,
          board: "commander",
        });
      }

      // Save preferences if any were set
      if (powerLevel || strategyNotes || budget) {
        await updateDeckPreferences(deck.id, {
          power_level: powerLevel || null,
          strategy_notes: strategyNotes || null,
          budget: budget || null,
        });
      }

      onCreated(deck);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create deck");
    } finally {
      setLoading(false);
    }
  }

  function handleSkipCommander() {
    setStep("preferences");
  }

  function handleSkipPreferences() {
    createAndFinish();
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
            {step === "basics" && "New Deck"}
            {step === "commander" && "Choose Commander"}
            {step === "preferences" && "Deck Preferences"}
          </div>
          <div className="flex items-center gap-3">
            {/* Step indicator */}
            {format === "commander" && (
              <div className="flex gap-1">
                {["basics", "commander", "preferences"].map((s, i) => (
                  <div
                    key={s}
                    className={`w-1.5 h-1.5 rounded-full ${
                      s === step ? "bg-accent-green" : "bg-border"
                    }`}
                  />
                ))}
              </div>
            )}
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-primary transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 px-3 py-2 bg-accent-red/10 border border-accent-red/30 rounded text-accent-red text-sm">
            {error}
          </div>
        )}

        {/* Step 1: Basics */}
        {step === "basics" && (
          <form onSubmit={handleBasicsSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-text-secondary mb-1.5">name</label>
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
              <label className="block text-xs text-text-secondary mb-1.5">format</label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className="input-terminal"
              >
                {FORMATS.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                description <span className="text-text-muted">(optional)</span>
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
              <button type="button" onClick={onClose} className="btn-ghost flex-1">cancel</button>
              <button type="submit" className="btn-primary flex-1">
                {format === "commander" ? "next →" : "create deck →"}
              </button>
            </div>
          </form>
        )}

        {/* Step 2: Commander */}
        {step === "commander" && (
          <div className="space-y-4">
            <p className="text-xs text-text-secondary">
              Search for a legendary creature to lead your deck.
            </p>

            {/* Commander search */}
            <div className="relative">
              <label className="block text-xs text-text-secondary mb-1.5">commander</label>
              <input
                type="text"
                value={commanderQuery}
                onChange={(e) => {
                  setCommanderQuery(e.target.value);
                  setSelectedCommander(null);
                  setError("");
                }}
                className="input-terminal"
                placeholder="Search for a legendary creature..."
                autoFocus
              />
              {showDropdown && commanderSuggestions.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-bg-secondary border border-border rounded-lg max-h-48 overflow-y-auto">
                  {commanderSuggestions.map((name) => (
                    <button
                      key={name}
                      onClick={() => handleSelectCommanderName(name)}
                      className="w-full text-left px-3 py-2 text-sm text-text-primary hover:bg-bg-hover transition-colors"
                    >
                      {name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Selected commander preview */}
            {searchingCommander && (
              <div className="text-xs text-text-muted">
                searching...<span className="animate-pulse">█</span>
              </div>
            )}

            {selectedCommander && (
              <div className="flex gap-3 p-3 bg-bg-primary rounded border border-accent-green/30">
                {(selectedCommander.image_uris?.small || selectedCommander.card_faces?.[0]?.image_uris?.small) && (
                  <img
                    src={selectedCommander.image_uris?.small || selectedCommander.card_faces?.[0]?.image_uris?.small}
                    alt={selectedCommander.name}
                    className="w-16 rounded"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary">{selectedCommander.name}</p>
                  <p className="text-xxs text-text-secondary mt-0.5">{selectedCommander.type_line}</p>
                  <p className="text-xxs text-text-muted mt-1 line-clamp-2">{selectedCommander.oracle_text}</p>
                  <div className="flex gap-1 mt-1">
                    {selectedCommander.color_identity?.map((c) => (
                      <span key={c} className="text-xxs px-1 py-0.5 rounded bg-bg-tertiary text-text-secondary">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <button onClick={() => setStep("basics")} className="btn-ghost flex-1">← back</button>
              <button onClick={handleSkipCommander} className="btn-ghost text-xs text-text-muted">skip</button>
              <button
                onClick={handleCommanderSubmit}
                disabled={!selectedCommander}
                className="btn-primary flex-1"
              >
                next →
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Preferences */}
        {step === "preferences" && (
          <div className="space-y-4">
            <p className="text-xs text-text-secondary">
              Optional — helps the AI give better suggestions.
            </p>

            <div>
              <label className="block text-xs text-text-secondary mb-1.5">power level</label>
              <select
                value={powerLevel}
                onChange={(e) => setPowerLevel(e.target.value)}
                className="input-terminal"
              >
                {POWER_LEVELS.map((pl) => (
                  <option key={pl.value} value={pl.value}>{pl.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                strategy notes <span className="text-text-muted">(what's the game plan?)</span>
              </label>
              <textarea
                value={strategyNotes}
                onChange={(e) => setStrategyNotes(e.target.value)}
                className="input-terminal min-h-[60px] resize-y"
                placeholder="Ramp into big creatures, use commander for card draw..."
              />
            </div>

            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                budget <span className="text-text-muted">(optional)</span>
              </label>
              <input
                type="text"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                className="input-terminal"
                placeholder="$50, no limit, etc."
              />
            </div>

            <div className="flex gap-2 pt-2">
              <button onClick={() => format === "commander" ? setStep("commander") : setStep("basics")} className="btn-ghost flex-1">← back</button>
              <button onClick={handleSkipPreferences} className="btn-ghost text-xs text-text-muted">skip</button>
              <button
                onClick={handlePreferencesSubmit}
                disabled={loading}
                className="btn-primary flex-1"
              >
                {loading ? (
                  <span>creating<span className="animate-pulse">...</span></span>
                ) : (
                  "create deck →"
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
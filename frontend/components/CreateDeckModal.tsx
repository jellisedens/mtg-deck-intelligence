"use client";

import { useState, useEffect, FormEvent } from "react";
import { createDeck, autocompleteCards, searchCards, addCard, updateDeckPreferences, getToken } from "@/lib/api";
import { Deck, ScryfallCard } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

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
  { value: "casual", label: "casual — fun first, no pubstomping" },
  { value: "focused", label: "focused — has a plan, not fully optimized" },
  { value: "optimized", label: "optimized — tuned, efficient, strong" },
  { value: "cedh", label: "cEDH — competitive, fast combos, no holds barred" },
];

const SHELL_MESSAGES_STARTER = [
  "fetching EDHREC data...",
  "analyzing commander synergies...",
  "building mana base...",
  "selecting staples...",
  "assembling your deck...",
];

const SHELL_MESSAGES_AVERAGE = [
  "fetching EDHREC data...",
  "analyzing community decklists...",
  "selecting most popular cards...",
  "building optimized mana base...",
  "adding utility lands...",
  "assembling full decklist...",
];

type GenerateMode = "none" | "starter" | "average";

interface Props {
  onClose: () => void;
  onCreated: (deck: Deck) => void;
}

export default function CreateDeckModal({ onClose, onCreated }: Props) {
  const [step, setStep] = useState<"basics" | "commander" | "preferences" | "generating">("basics");

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
  const [colorPreferences, setColorPreferences] = useState("");
  const [cardTypePreferences, setCardTypePreferences] = useState("");
  const [budget, setBudget] = useState("");
  const [otherNotes, setOtherNotes] = useState("");
  const [generateMode, setGenerateMode] = useState<GenerateMode>("starter");

  // Step 4: Generating
  const [shellProgress, setShellProgress] = useState(0);
  const [shellMessage, setShellMessage] = useState("");
  const [shellResult, setShellResult] = useState<{
    cards_added: number;
    total_deck_size: number;
    edhrec_decks_analyzed: number;
    mode: string;
  } | null>(null);

  // Shared
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Animate shell progress messages
  useEffect(() => {
    if (step !== "generating") return;
    const messages = generateMode === "average" ? SHELL_MESSAGES_AVERAGE : SHELL_MESSAGES_STARTER;
    setShellMessage(messages[0]);
    const interval = setInterval(() => {
      setShellProgress((prev) => {
        const next = Math.min(prev + 1, messages.length - 1);
        setShellMessage(messages[next]);
        return next;
      });
    }, 2500);
    return () => clearInterval(interval);
  }, [step, generateMode]);

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
      const results = await searchCards(`!"${cardName}" t:legendary`);
      if (results.length > 0) {
        setSelectedCommander(results[0]);
        setCommanderResults([]);
      } else {
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
      const deck = await createDeck({
        name: name.trim(),
        format,
        description: description.trim() || undefined,
      });

      if (format === "commander" && selectedCommander) {
        await addCard(deck.id, {
          scryfall_id: selectedCommander.id,
          card_name: selectedCommander.name,
          quantity: 1,
          board: "commander",
        });
      }

      // Save all preferences
      const hasPreferences = powerLevel || strategyNotes || colorPreferences || cardTypePreferences || budget || otherNotes;
      if (hasPreferences) {
        await updateDeckPreferences(deck.id, {
          power_level: powerLevel || null,
          strategy_notes: strategyNotes || null,
          color_preferences: colorPreferences || null,
          card_type_preferences: cardTypePreferences || null,
          budget: budget || null,
          other_notes: otherNotes || null,
        });
      }

      // Generate shell if requested
      if (generateMode !== "none" && format === "commander" && selectedCommander) {
        setStep("generating");
        setShellProgress(0);

        try {
          const token = getToken();
          const res = await fetch(`${API_URL}/decks/${deck.id}/wizard/generate-shell`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ mode: generateMode }),
          });

          if (res.ok) {
            const result = await res.json();
            setShellResult({
              cards_added: result.cards_added,
              total_deck_size: result.total_deck_size,
              edhrec_decks_analyzed: result.edhrec_decks_analyzed,
              mode: result.mode,
            });
            await new Promise((r) => setTimeout(r, 1500));
          } else {
            console.error("Shell generation failed:", await res.text());
          }
        } catch (err) {
          console.error("Shell generation error:", err);
        }
      }

      onCreated(deck);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create deck");
      setStep("preferences");
    } finally {
      setLoading(false);
    }
  }

  function handleSkipCommander() {
    setStep("preferences");
  }

  function handleSkipPreferences() {
    setGenerateMode("none");
    createAndFinish();
  }

  const shellMessages = generateMode === "average" ? SHELL_MESSAGES_AVERAGE : SHELL_MESSAGES_STARTER;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={step === "generating" ? undefined : onClose}
    >
      <div
        className="panel p-6 w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="text-xs text-text-muted font-medium uppercase tracking-wider">
            {step === "basics" && "New Deck"}
            {step === "commander" && "Choose Commander"}
            {step === "preferences" && "Deck Preferences"}
            {step === "generating" && "Building Deck"}
          </div>
          <div className="flex items-center gap-3">
            {format === "commander" && (
              <div className="flex gap-1">
                {["basics", "commander", "preferences", "generating"].map((s) => (
                  <div
                    key={s}
                    className={`w-1.5 h-1.5 rounded-full ${
                      s === step ? "bg-accent-green" : "bg-border"
                    }`}
                  />
                ))}
              </div>
            )}
            {step !== "generating" && (
              <button
                onClick={onClose}
                className="text-text-muted hover:text-text-primary transition-colors"
              >
                ✕
              </button>
            )}
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
              All optional — helps the AI give better suggestions.
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
                strategy / theme
              </label>
              <textarea
                value={strategyNotes}
                onChange={(e) => setStrategyNotes(e.target.value)}
                className="input-terminal min-h-[50px] resize-y"
                placeholder="Ramp into big creatures, life drain theme..."
              />
            </div>

            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                color preferences
              </label>
              <input
                type="text"
                value={colorPreferences}
                onChange={(e) => setColorPreferences(e.target.value)}
                className="input-terminal"
                placeholder="Heavy black, splash green for ramp..."
              />
            </div>

            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                card type preferences
              </label>
              <input
                type="text"
                value={cardTypePreferences}
                onChange={(e) => setCardTypePreferences(e.target.value)}
                className="input-terminal"
                placeholder="Creature-heavy, minimal enchantments..."
              />
            </div>

            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                budget
              </label>
              <input
                type="text"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                className="input-terminal"
                placeholder="$50, no limit, no cards over $10, etc."
              />
            </div>

            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                other notes
              </label>
              <input
                type="text"
                value={otherNotes}
                onChange={(e) => setOtherNotes(e.target.value)}
                className="input-terminal"
                placeholder="No infinite combos, playgroup has lots of flyers..."
              />
            </div>

            {/* Generation mode selector */}
            {format === "commander" && selectedCommander && (
              <div className="space-y-2 pt-1">
                <label className="block text-xs text-text-secondary mb-1">deck generation</label>

                <label className="flex items-start gap-3 p-3 bg-bg-primary rounded border border-border cursor-pointer hover:border-text-muted transition-colors">
                  <input
                    type="radio"
                    name="generate-mode"
                    checked={generateMode === "average"}
                    onChange={() => setGenerateMode("average")}
                    className="mt-0.5 accent-accent-green"
                  />
                  <div className="text-xs">
                    <span className="text-text-primary font-medium">Generate average {selectedCommander.name} deck</span>
                    <br />
                    <span className="text-text-muted">
                      Builds a complete 99-card deck based on EDHREC community data.
                      The most popular cards across thousands of decks.
                    </span>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 bg-bg-primary rounded border border-border cursor-pointer hover:border-text-muted transition-colors">
                  <input
                    type="radio"
                    name="generate-mode"
                    checked={generateMode === "starter"}
                    onChange={() => setGenerateMode("starter")}
                    className="mt-0.5 accent-accent-green"
                  />
                  <div className="text-xs">
                    <span className="text-text-primary font-medium">Generate starter shell</span>
                    <br />
                    <span className="text-text-muted">
                      Adds ~25 staples + lands. Leaves room for you to customize.
                    </span>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 bg-bg-primary rounded border border-border cursor-pointer hover:border-text-muted transition-colors">
                  <input
                    type="radio"
                    name="generate-mode"
                    checked={generateMode === "none"}
                    onChange={() => setGenerateMode("none")}
                    className="mt-0.5 accent-accent-green"
                  />
                  <div className="text-xs">
                    <span className="text-text-primary font-medium">Empty deck</span>
                    <br />
                    <span className="text-text-muted">
                      Just the commander. Build from scratch.
                    </span>
                  </div>
                </label>
              </div>
            )}

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
                ) : generateMode === "average" ? (
                  `generate ${selectedCommander?.name?.split(",")[0] || ""} deck →`
                ) : generateMode === "starter" ? (
                  "create & build →"
                ) : (
                  "create deck →"
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Generating Shell */}
        {step === "generating" && (
          <div className="space-y-6 py-4">
            <div className="text-center">
              {!shellResult ? (
                <>
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-accent-green/10 mb-4">
                    <svg className="w-6 h-6 text-accent-green animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </div>
                  <p className="text-sm text-text-primary font-medium mb-2">
                    {generateMode === "average"
                      ? `Building average ${selectedCommander?.name} deck`
                      : `Building your ${selectedCommander?.name} deck`
                    }
                  </p>
                  <p className="text-xs text-text-muted animate-pulse">
                    {shellMessage}
                  </p>
                  <div className="mt-4 mx-8 h-1 bg-bg-tertiary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent-green rounded-full transition-all duration-1000 ease-out"
                      style={{ width: `${((shellProgress + 1) / shellMessages.length) * 100}%` }}
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-accent-green/10 mb-4">
                    <svg className="w-6 h-6 text-accent-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-sm text-text-primary font-medium mb-1">
                    {shellResult.mode === "average" ? "Average deck built!" : "Deck ready!"}
                  </p>
                  <p className="text-xs text-text-muted">
                    {shellResult.cards_added} cards added from {shellResult.edhrec_decks_analyzed.toLocaleString()} community decks
                  </p>
                  <p className="text-xs text-text-muted mt-1">
                    {shellResult.total_deck_size}/100 cards
                    {shellResult.total_deck_size < 100 && " — use the AI panel to fill the rest"}
                  </p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
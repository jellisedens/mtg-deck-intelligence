"use client";

import { useState, useEffect } from "react";
import { updateDeckPreferences } from "@/lib/api";

interface Props {
  deckId: string;
  currentPreferences: Record<string, string | null> | null;
  onSaved: () => void;
}

const POWER_LEVELS = [
  { value: "", label: "not set" },
  { value: "casual", label: "casual — fun first, no pubstomping" },
  { value: "focused", label: "focused — has a plan, not fully optimized" },
  { value: "optimized", label: "optimized — tuned, efficient, strong" },
  { value: "cedh", label: "cEDH — competitive, fast combos, no holds barred" },
];

export default function DeckPreferences({ deckId, currentPreferences, onSaved }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [strategyNotes, setStrategyNotes] = useState("");
  const [colorPreferences, setColorPreferences] = useState("");
  const [cardTypePreferences, setCardTypePreferences] = useState("");
  const [budget, setBudget] = useState("");
  const [powerLevel, setPowerLevel] = useState("");
  const [otherNotes, setOtherNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    if (currentPreferences) {
      setStrategyNotes(currentPreferences.strategy_notes || "");
      setColorPreferences(currentPreferences.color_preferences || "");
      setCardTypePreferences(currentPreferences.card_type_preferences || "");
      setBudget(currentPreferences.budget || "");
      setPowerLevel(currentPreferences.power_level || "");
      setOtherNotes(currentPreferences.other_notes || "");
    }
  }, [currentPreferences]);

  async function handleSave() {
    setSaving(true);
    try {
      console.log("[PREFS] Saving:", {
        strategy_notes: strategyNotes || null,
        color_preferences: colorPreferences || null,
        card_type_preferences: cardTypePreferences || null,
        budget: budget || null,
        power_level: powerLevel || null,
        other_notes: otherNotes || null,
      });
      await updateDeckPreferences(deckId, {
        strategy_notes: strategyNotes || null,
        color_preferences: colorPreferences || null,
        card_type_preferences: cardTypePreferences || null,
        budget: budget || null,
        power_level: powerLevel || null,
        other_notes: otherNotes || null,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onSaved();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "Failed to save preferences");
    } finally {
      setSaving(false);
    }
  }

  const hasPreferences = strategyNotes || colorPreferences || cardTypePreferences || budget || powerLevel || otherNotes;

  return (
    <div className="panel">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-bg-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted font-medium uppercase tracking-wider">
            Preferences
          </span>
          {hasPreferences && !expanded && (
            <span className="text-xxs text-accent-green">configured</span>
          )}
        </div>
        <span className="text-text-muted text-xs">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          <p className="text-xxs text-text-muted">
            these preferences guide AI suggestions to match your vision for the deck
          </p>

          <div>
            <label className="block text-xxs text-text-secondary mb-1">
              power level
            </label>
            <select
              value={powerLevel}
              onChange={(e) => setPowerLevel(e.target.value)}
              className="input-terminal text-xs w-full"
            >
              {POWER_LEVELS.map((pl) => (
                <option key={pl.value} value={pl.value}>
                  {pl.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xxs text-text-secondary mb-1">
              strategy / theme
            </label>
            <textarea
              value={strategyNotes}
              onChange={(e) => setStrategyNotes(e.target.value)}
              className="input-terminal text-xs min-h-[50px] resize-y w-full"
              placeholder="e.g., aggressive dragon tribal, ramp into big flyers, win through combat damage"
            />
          </div>

          <div>
            <label className="block text-xxs text-text-secondary mb-1">
              color preferences
            </label>
            <input
              type="text"
              value={colorPreferences}
              onChange={(e) => setColorPreferences(e.target.value)}
              className="input-terminal text-xs"
              placeholder="e.g., lean more into red and green, minimize white"
            />
          </div>

          <div>
            <label className="block text-xxs text-text-secondary mb-1">
              card type preferences
            </label>
            <input
              type="text"
              value={cardTypePreferences}
              onChange={(e) => setCardTypePreferences(e.target.value)}
              className="input-terminal text-xs"
              placeholder="e.g., prefer creatures over enchantments, more instant-speed interaction"
            />
          </div>

          <div>
            <label className="block text-xxs text-text-secondary mb-1">
              budget
            </label>
            <input
              type="text"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className="input-terminal text-xs"
              placeholder="e.g., no cards over $20, total deck under $200"
            />
          </div>

          <div>
            <label className="block text-xxs text-text-secondary mb-1">
              other notes
            </label>
            <textarea
              value={otherNotes}
              onChange={(e) => setOtherNotes(e.target.value)}
              className="input-terminal text-xs min-h-[40px] resize-y w-full"
              placeholder="e.g., my playgroup doesn't allow infinite combos, prefer cards from recent sets"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary text-xs"
            >
              {saving ? "saving..." : "save preferences"}
            </button>
            {saved && (
              <span className="text-accent-green text-xs">saved</span>
            )}
            {saveError && (
              <span className="text-accent-red text-xs">{saveError}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
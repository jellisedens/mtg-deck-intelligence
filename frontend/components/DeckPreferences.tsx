"use client";

import { useState, useEffect } from "react";
import { updateDeckPreferences } from "@/lib/api";

interface Props {
  deckId: string;
  currentPreferences: Record<string, string | null> | null;
  onSaved: () => void;
}

export default function DeckPreferences({ deckId, currentPreferences, onSaved }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [strategyNotes, setStrategyNotes] = useState("");
  const [colorPreferences, setColorPreferences] = useState("");
  const [cardTypePreferences, setCardTypePreferences] = useState("");
  const [budget, setBudget] = useState("");
  const [otherNotes, setOtherNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (currentPreferences) {
      setStrategyNotes(currentPreferences.strategy_notes || "");
      setColorPreferences(currentPreferences.color_preferences || "");
      setCardTypePreferences(currentPreferences.card_type_preferences || "");
      setBudget(currentPreferences.budget || "");
      setOtherNotes(currentPreferences.other_notes || "");
    }
  }, [currentPreferences]);

  async function handleSave() {
    setSaving(true);
    try {
      await updateDeckPreferences(deckId, {
        strategy_notes: strategyNotes || null,
        color_preferences: colorPreferences || null,
        card_type_preferences: cardTypePreferences || null,
        budget: budget || null,
        other_notes: otherNotes || null,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onSaved();
    } catch {
      // silently fail
    } finally {
      setSaving(false);
    }
  }

  const hasPreferences = strategyNotes || colorPreferences || cardTypePreferences || budget || otherNotes;

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
          </div>
        </div>
      )}
    </div>
  );
}
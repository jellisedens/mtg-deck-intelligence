"use client";

import { useState, useEffect } from "react";
import { ScryfallCard, DeckCard } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

const AVAILABLE_ROLES = [
  "ramp", "card_draw", "removal", "board_wipe", "protection",
  "tutor", "tokens", "recursion", "finisher", "utility",
];

function CardImage({ scryfallId }: { scryfallId: string }) {
  const [error, setError] = useState(false);

  if (error) return null;

  return (
    <img
      src={`https://api.scryfall.com/cards/${scryfallId}?format=image&version=normal`}
      alt=""
      className="w-56 rounded shadow-lg"
      onError={() => setError(true)}
      loading="lazy"
    />
  );
}

function ScoreBadge({ score }: { score: number }) {
  let color = "text-text-muted bg-bg-tertiary";
  let label = "—";

  if (score >= 9) {
    color = "text-accent-green bg-accent-green/10 border border-accent-green/30";
    label = "core";
  } else if (score >= 7) {
    color = "text-accent-blue bg-accent-blue/10 border border-accent-blue/30";
    label = "strong";
  } else if (score >= 5) {
    color = "text-accent-yellow bg-accent-yellow/10 border border-accent-yellow/30";
    label = "solid";
  } else {
    color = "text-accent-red bg-accent-red/10 border border-accent-red/30";
    label = "cuttable";
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {score}/10 — {label}
    </span>
  );
}

interface Props {
  cardData: ScryfallCard;
  deckCard: DeckCard;
  tags?: string[];
  deckId: string;
  onUpdateNotes: (cardId: string, notes: string) => void;
  onRolesUpdated?: () => void;
}

export default function CardDetail({ cardData, deckCard, tags = [], deckId, onUpdateNotes, onRolesUpdated }: Props) {
  const [notes, setNotes] = useState(deckCard.notes || "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [roles, setRoles] = useState<string[]>(deckCard.ai_context?.roles || []);
  const [roleSaving, setRoleSaving] = useState(false);
  const [deckRolesList, setDeckRolesList] = useState<string[]>([]);
  const aiContext = deckCard.ai_context;


  useEffect(() => {
    async function fetchDeckRoles() {
      try {
        const token = localStorage.getItem("mtg_token");
        const res = await fetch(`${API_BASE}/decks/${deckId}/roles`, {
          headers: { Authorization: `Bearer ${token || ""}` },
        });
        if (res.ok) {
          const data = await res.json();
          const customRoles = (data.roles || [])
            .map((r: { role: string }) => r.role)
            .filter((r: string) => !AVAILABLE_ROLES.includes(r));
          setDeckRolesList(customRoles);
        }
      } catch {
        // silent
      }
    }
    fetchDeckRoles();
  }, [deckId]);

  useEffect(() => {
    setNotes(deckCard.notes || "");
    setRoles(deckCard.ai_context?.roles || []);
  }, [deckCard.notes, deckCard.ai_context]);

  async function handleSaveNotes() {
    setSaving(true);
    onUpdateNotes(deckCard.id, notes);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function toggleRole(role: string) {
    const newRoles = roles.includes(role)
      ? roles.filter(r => r !== role)
      : [...roles, role];
    
    setRoles(newRoles);
    setRoleSaving(true);

    try {
      const token = localStorage.getItem("mtg_token");
      const res = await fetch(`${API_BASE}/decks/${deckId}/cards/${deckCard.id}/roles`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(newRoles),
      });
      if (!res.ok) {
        setRoles(roles);
      } else {
        if (onRolesUpdated) onRolesUpdated();
        // If adding a custom role, add to local deck roles list
        if (!AVAILABLE_ROLES.includes(role) && !deckRolesList.includes(role) && newRoles.includes(role)) {
          setDeckRolesList(prev => [...prev, role]);
        }
      }
    } catch {
      setRoles(roles);
    } finally {
      setRoleSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Card image */}
        <div>
          <CardImage scryfallId={cardData.id} />
        </div>

        {/* Card info */}
        <div className="space-y-3 text-sm">
          <div>
            <span className="text-xxs text-text-muted uppercase tracking-wider">type</span>
            <p className="text-text-primary">{cardData.type_line}</p>
          </div>

          {cardData.oracle_text && (
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">text</span>
              <p className="text-text-secondary text-xs leading-relaxed whitespace-pre-line">
                {cardData.oracle_text}
              </p>
            </div>
          )}

          {cardData.power && cardData.toughness && (
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">p/t</span>
              <p className="text-text-primary">{cardData.power}/{cardData.toughness}</p>
            </div>
          )}

          <div className="flex gap-4">
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">set</span>
              <p className="text-text-secondary text-xs">{cardData.set_name}</p>
            </div>
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">rarity</span>
              <p className="text-text-secondary text-xs">{cardData.rarity}</p>
            </div>
          </div>

          {cardData.prices?.usd && (
            <div>
              <span className="text-xxs text-text-muted uppercase tracking-wider">price</span>
              <p className="text-accent-green text-xs">
                ${cardData.prices.usd}
                {cardData.prices.usd_foil && (
                  <span className="text-text-muted ml-2">foil: ${cardData.prices.usd_foil}</span>
                )}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Auto-detected tags (from Scryfall Oracle Tag index) */}
      {tags.length > 0 && (
        <div className="border-t border-border pt-3">
          <span className="text-xxs text-text-muted uppercase tracking-wider">auto tags</span>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="text-xxs px-2 py-0.5 rounded border border-accent-blue/30 text-accent-blue bg-accent-blue/10"
              >
                {tag.replace("_", " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* User role tags */}
      <div className="border-t border-border pt-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xxs text-text-muted uppercase tracking-wider">card roles</span>
          {roleSaving && <span className="text-xxs text-text-muted animate-pulse">saving...</span>}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {AVAILABLE_ROLES.map(role => (
            <button
              key={role}
              onClick={() => toggleRole(role)}
              className={`text-xxs px-2 py-0.5 rounded border transition-colors ${
                roles.includes(role)
                  ? "border-accent-green text-accent-green bg-accent-green/10"
                  : "border-border text-text-muted hover:text-text-secondary"
              }`}
            >
              {role.replace("_", " ")}
            </button>
          ))}
          {/* Custom roles from this deck */}
          {deckRolesList.map(role => (
            <button
              key={role}
              onClick={() => toggleRole(role)}
              className={`text-xxs px-2 py-0.5 rounded border transition-colors ${
                roles.includes(role)
                  ? "border-accent-green text-accent-green bg-accent-green/10"
                  : "border-border text-text-muted hover:text-text-secondary"
              }`}
            >
              {role.replace("_", " ")}
            </button>
          ))}
          {/* Active custom roles on this card not yet in deck list */}
          {roles.filter(r => !AVAILABLE_ROLES.includes(r) && !deckRolesList.includes(r)).map(role => (
            <button
              key={role}
              onClick={() => toggleRole(role)}
              className="text-xxs px-2 py-0.5 rounded border border-accent-green text-accent-green bg-accent-green/10"
            >
              {role.replace("_", " ")} ✕
            </button>
          ))}
        </div>
        <div className="flex gap-1 mt-1.5">
          <input
            type="text"
            placeholder="custom role..."
            className="input-terminal text-xxs w-32"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const input = e.currentTarget;
                const value = input.value.trim().toLowerCase().replace(/\s+/g, "_");
                if (value && !roles.includes(value)) {
                  toggleRole(value);
                }
                input.value = "";
              }
            }}
          />
          <span className="text-xxs text-text-muted self-center">enter to add</span>
        </div>
        {roles.length > 0 && (
          <p className="text-xxs text-text-muted mt-1">
            assigned: {roles.map(r => r.replace("_", " ")).join(", ")}
          </p>
        )}
      </div>

      {/* AI Context section */}
      {aiContext && (
        <div className="border-t border-border pt-3">
          <div className="text-xxs text-text-muted uppercase tracking-wider mb-2">
            AI Analysis
          </div>

          <div className="space-y-2">
            {aiContext.impact_score && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-secondary">impact:</span>
                <ScoreBadge score={aiContext.impact_score} />
                {aiContext.is_critical && (
                  <span className="text-xxs text-accent-green bg-accent-green/10 px-1.5 py-0.5 rounded border border-accent-green/30">
                    critical
                  </span>
                )}
              </div>
            )}

            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-text-secondary">ai role:</span>
              <span className="text-xs text-text-primary bg-bg-tertiary px-1.5 py-0.5 rounded">
                {aiContext.role}
              </span>
              {aiContext.secondary_roles?.map((role) => (
                <span key={role} className="text-xxs text-text-muted bg-bg-tertiary px-1.5 py-0.5 rounded">
                  {role}
                </span>
              ))}
            </div>

            {aiContext.impact_reason && (
              <div>
                <span className="text-xs text-text-secondary">assessment: </span>
                <span className="text-xs text-text-primary">{aiContext.impact_reason}</span>
              </div>
            )}

            {aiContext.synergy_notes && (
              <div>
                <span className="text-xs text-text-secondary">synergy: </span>
                <span className="text-xs text-text-primary">{aiContext.synergy_notes}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* User notes section */}
      <div className="border-t border-border pt-3">
        <div className="text-xxs text-text-muted uppercase tracking-wider mb-2">
          Your Notes
        </div>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="input-terminal text-xs min-h-[60px] resize-y w-full"
          placeholder="Add notes about this card... (strategy thoughts, combo pieces, upgrade plans)"
        />
        <div className="flex items-center gap-2 mt-2">
          <button
            onClick={handleSaveNotes}
            disabled={saving || notes === (deckCard.notes || "")}
            className="btn-primary text-xs px-3 py-1"
          >
            {saving ? "saving..." : "save notes"}
          </button>
          {saved && <span className="text-accent-green text-xs">saved</span>}
        </div>
      </div>
    </div>
  );
}
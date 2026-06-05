"use client";

import { useState, useRef, useEffect } from "react";
import { aiSuggest } from "@/lib/api";
import { AISuggestionResponse, CardSuggestion, CutSuggestion } from "@/lib/types";

interface Message {
  role: "user" | "ai";
  content: string;
  response?: AISuggestionResponse;
  loading?: boolean;
  error?: string;
}

interface Props {
  deckId: string;
  onAddCard?: (scryfallId: string, cardName: string) => Promise<void>;
}

function SuggestionCardRow({
  card,
  onAdd,
}: {
  card: CardSuggestion;
  onAdd?: (scryfallId: string, cardName: string) => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [added, setAdded] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  return (
    <div className="border border-border rounded p-2 hover:bg-bg-hover transition-colors">
      <div className="flex items-start gap-3 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-text-primary font-medium">{card.card_name}</span>
            {card.price_usd && (
              <span className="text-xxs text-accent-green">${card.price_usd}</span>
            )}
            {card.category && (
              <span className="text-xxs text-text-muted bg-bg-tertiary px-1 py-0.5 rounded">
                {card.category}
              </span>
            )}
            {card.mana_cost && (
              <span className="text-xxs text-text-muted">{card.mana_cost}</span>
            )}
            <div className="flex items-center gap-1 ml-auto">
              {onAdd && card.scryfall_id && (
                <button
                  onClick={async (e) => {
                    e.stopPropagation();
                    if (added || adding) return;
                    setAdding(true);
                    setAddError(null);
                    try {
                      await onAdd(card.scryfall_id!, card.card_name);
                      setAdded(true);
                      setTimeout(() => setAdded(false), 3000);
                    } catch (err: unknown) {
                      const msg = err instanceof Error ? err.message : "Failed to add";
                      setAddError(msg.length > 30 ? msg.slice(0, 30) + "…" : msg);
                      setTimeout(() => setAddError(null), 4000);
                    } finally {
                      setAdding(false);
                    }
                  }}
                  disabled={added || adding}
                  className={`text-xxs px-1.5 py-0.5 rounded transition-colors ${
                    added
                      ? "bg-accent-green/20 text-accent-green"
                      : addError
                      ? "bg-accent-red/20 text-accent-red"
                      : "bg-bg-tertiary text-text-muted hover:text-accent-green hover:bg-accent-green/10"
                  }`}
                >
                  {added ? "added ✓" : adding ? "..." : addError ? addError : "+ add"}
                </button>
              )}
              <span className="text-xxs text-text-muted">{expanded ? "▲" : "▼"}</span>
            </div>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">{card.reasoning}</p>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 p-3 bg-bg-primary rounded border border-border">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {card.scryfall_id && !imgError && (
              <div>
                <img
                  src={`https://api.scryfall.com/cards/${card.scryfall_id}?format=image&version=normal`}
                  alt={card.card_name}
                  className="w-56 rounded shadow-lg"
                  onError={() => setImgError(true)}
                  loading="lazy"
                />
              </div>
            )}
            <div className="space-y-3 text-sm">
              {card.type_line && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">type</span>
                  <p className="text-text-primary">{card.type_line}</p>
                </div>
              )}
              {card.mana_cost && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">mana cost</span>
                  <p className="text-text-primary">{card.mana_cost}</p>
                </div>
              )}
              {card.price_usd && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">price</span>
                  <p className="text-accent-green text-xs">${card.price_usd}</p>
                </div>
              )}
              {card.priority && (
                <div>
                  <span className="text-xxs text-text-muted uppercase tracking-wider">priority</span>
                  <p className="text-text-primary text-xs">{card.priority}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CutCardRow({ cut }: { cut: CutSuggestion }) {
  return (
    <div className="border border-accent-red/20 rounded p-2">
      <div className="flex items-center gap-2">
        <span className="text-sm text-text-primary font-medium">{cut.card_name}</span>
        {cut.impact_score && (
          <span className="text-xxs text-accent-red bg-accent-red/10 px-1 py-0.5 rounded">
            impact: {cut.impact_score}/10
          </span>
        )}
      </div>
      <p className="text-xs text-text-secondary mt-0.5">{cut.reasoning}</p>
    </div>
  );
}

function AIResponse({
  response,
  onOptionClick,
  onAddCard,
  filters,
}: {
  response: AISuggestionResponse;
  onOptionClick?: (option: string) => void;
  onAddCard?: (scryfallId: string, cardName: string) => Promise<void>;
  filters?: { maxCmc: number | null; maxPrice: number | null; types: string[] };
}) {
  return (
    <div className="space-y-3">
      {/* Summary */}
      {response.summary && (
        <div className="text-xs text-text-secondary leading-relaxed whitespace-pre-line">
          {response.summary}
        </div>
      )}

      {/* Strategy notes */}
      {response.strategy_notes && (
        <div className="text-xs text-text-secondary leading-relaxed whitespace-pre-line">
          {response.strategy_notes}
        </div>
      )}

      {/* Card suggestions */}
      {response.suggestions.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xxs text-text-muted uppercase tracking-wider">
            suggestions ({response.suggestions.length})
          </div>
          {response.suggestions
            .filter((card) => {
              if (!filters) return true;
              if (filters.maxCmc !== null) {
                const cmc = parseInt(card.mana_cost?.replace(/[^0-9]/g, "") || "0") || 0;
                // Use the actual CMC from type_line parsing — rough but works
                const cmcMatch = card.mana_cost?.match(/\{(\d+)\}/);
                const colorPips = (card.mana_cost?.match(/\{[WUBRG]\}/g) || []).length;
                const genericCost = cmcMatch ? parseInt(cmcMatch[1]) : 0;
                const totalCmc = genericCost + colorPips;
                if (totalCmc > filters.maxCmc) return false;
              }
              if (filters.maxPrice !== null && card.price_usd) {
                if (parseFloat(card.price_usd) > filters.maxPrice) return false;
              }
              if (filters.types && filters.types.length > 0) {
                const typeLine = card.type_line || "";
                const matchesType = filters.types.some(t => typeLine.includes(t));
                if (!matchesType) return false;
              }
              return true;
            })
            .map((card, i) => (
            <SuggestionCardRow
              key={`${card.card_name}-${i}`}
              card={card}
              onAdd={onAddCard}
            />
          ))}
        </div>
      )}

      {/* Cut suggestions */}
      {response.cuts.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xxs text-text-muted uppercase tracking-wider">
            recommended cuts ({response.cuts.length})
          </div>
          {response.cuts.map((cut, i) => (
            <CutCardRow key={`${cut.card_name}-${i}`} cut={cut} />
          ))}
        </div>
      )}

      {/* Clarification — now with clickable options */}
      {response.needs_clarification && response.clarification_question && (
        <div className="space-y-2">
          <div className="text-xs text-accent-yellow">
            {response.clarification_question}
          </div>
          {response.clarification_options && response.clarification_options.length > 0 && (
            <div className="space-y-1">
              {response.clarification_options.map((option, i) => (
                <button
                  key={i}
                  onClick={() => onOptionClick?.(option.description || option.label)}
                  className="block w-full text-left text-xs text-text-secondary hover:text-accent-green px-3 py-1.5 rounded hover:bg-bg-hover transition-colors border border-border"
                >
                  <span className="text-accent-green mr-1">→</span>
                  <span className="font-medium">{option.label}</span>
                  {option.description && (
                    <span className="text-text-muted ml-1">— {option.description}</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AISuggestPanel({ deckId, onAddCard }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [conversationHistory, setConversationHistory] = useState<Array<{
    role: string;
    content: string;
    cards_suggested?: string[];
    cards_accepted?: string[];
  }>>([]);
  const [lastClarificationCategory, setLastClarificationCategory] = useState<string | null>(null);
  const [mode, setMode] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    maxCmc: null as number | null,
    maxPrice: null as number | null,
    types: [] as string[],
  });
  const bottomRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (loading) {
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [loading]);

  async function sendPrompt(userMessage: string) {
    if (!userMessage.trim() || loading) return;

    let promptToSend = userMessage;
    if (lastClarificationCategory) {
      const vague = ["all types", "all", "everything", "any", "any type"];
      if (vague.includes(userMessage.toLowerCase().trim())) {
        promptToSend = `suggest all types of ${lastClarificationCategory}`;
      } else {
        promptToSend = `suggest ${userMessage.toLowerCase()} for ${lastClarificationCategory}`;
      }
      setLastClarificationCategory(null);
    }

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage },
      { role: "ai", content: "", loading: true },
    ]);
    setLoading(true);

    try {
      const response = await aiSuggest({
        prompt: promptToSend,
        deck_id: deckId,
        intent_override: mode || undefined,
        conversation_context: conversationHistory.length > 0 ? conversationHistory : undefined,
      });

      if (response.needs_clarification && (response as any)._original_category) {
        setLastClarificationCategory((response as any)._original_category);
      } else if (response.needs_clarification) {
        const question = response.clarification_question || "";
        const categoryMatch = question.match(/what (?:type|kind) of (\w+)/i);
        if (categoryMatch) {
          setLastClarificationCategory(categoryMatch[1].toLowerCase());
        }
      }

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "ai",
          content: "",
          response,
        };
        return updated;
      });
      // Track conversation for context
      const suggestedCards = response.suggestions?.map(s => s.card_name) || [];
      setConversationHistory(prev => [
        ...prev,
        { role: "user", content: promptToSend },
        { role: "ai", content: response.summary || "", cards_suggested: suggestedCards, cards_accepted: [] },
      ]);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "AI request failed";
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "ai",
          content: "",
          error: errorMsg,
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const userMessage = input.trim();
    setInput("");
    await sendPrompt(userMessage);
  }

  function handleOptionClick(option: string) {
    if (loading) return;
    sendPrompt(option);
  }

  return (
    <div className="panel flex flex-col h-[500px]">
      <div className="px-4 py-3 border-b border-border flex-shrink-0 space-y-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xxs text-text-muted font-medium uppercase tracking-wider mr-1">
            Mode:
          </span>
          {[
            { key: null, label: "Auto", icon: "✦" },
            { key: "suggest", label: "Suggest", icon: "💡" },
            { key: "cuts", label: "Cuts", icon: "✂️" },
            { key: "swap", label: "Swap", icon: "🔄" },
            { key: "discuss", label: "Discuss", icon: "💬" },
          ].map(({ key, label, icon }) => (
            <button
              key={label}
              onClick={() => setMode(key)}
              className={`text-xxs px-2 py-1 rounded transition-colors ${
                mode === key
                  ? "bg-accent-green/20 text-accent-green border border-accent-green/40"
                  : "bg-bg-tertiary text-text-muted hover:text-text-secondary border border-transparent"
              }`}
            >
              {icon} {label}
            </button>
          ))}
        </div>

        {(mode === "suggest" || mode === null) && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xxs text-text-muted">Filters:</span>
            <select
              value={filters.maxCmc ?? ""}
              onChange={(e) => setFilters(f => ({ ...f, maxCmc: e.target.value ? Number(e.target.value) : null }))}
              className="text-xxs bg-bg-tertiary text-text-secondary border border-border rounded px-1.5 py-0.5"
            >
              <option value="">CMC: Any</option>
              <option value="1">CMC ≤ 1</option>
              <option value="2">CMC ≤ 2</option>
              <option value="3">CMC ≤ 3</option>
              <option value="4">CMC ≤ 4</option>
              <option value="5">CMC ≤ 5</option>
              <option value="7">CMC ≤ 7</option>
            </select>
            <select
              value={filters.maxPrice ?? ""}
              onChange={(e) => setFilters(f => ({ ...f, maxPrice: e.target.value ? Number(e.target.value) : null }))}
              className="text-xxs bg-bg-tertiary text-text-secondary border border-border rounded px-1.5 py-0.5"
            >
              <option value="">Price: Any</option>
              <option value="1">≤ $1</option>
              <option value="5">≤ $5</option>
              <option value="10">≤ $10</option>
              <option value="25">≤ $25</option>
            </select>
            <div className="flex items-center gap-1 flex-wrap">
              {["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Equipment", "Land"].map((type) => (
                <button
                  key={type}
                  onClick={() => setFilters(f => ({
                    ...f,
                    types: f.types.includes(type)
                      ? f.types.filter(t => t !== type)
                      : [...f.types, type],
                  }))}
                  className={`text-xxs px-1.5 py-0.5 rounded transition-colors ${
                    filters.types.includes(type)
                      ? "bg-accent-green/20 text-accent-green border border-accent-green/40"
                      : "bg-bg-tertiary text-text-muted hover:text-text-secondary border border-transparent"
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
            {filters.maxCmc !== null || filters.maxPrice !== null || filters.types.length > 0 ? (
              <button
                onClick={() => setFilters({ maxCmc: null, maxPrice: null, types: [] })}
                className="text-xxs text-accent-red hover:text-accent-red/80 transition-colors"
              >
                reset
              </button>
            ) : null}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <p className="text-text-muted text-xs mb-3">try asking:</p>
            <div className="space-y-1.5">
              {[
                "suggest cards for my 2-drop slot",
                "what are the weakest cards I should cut?",
                "analyze my deck's strategy",
                "swap Fellwar Stone for something better",
              ].map((example) => (
                <button
                  key={example}
                  onClick={() => setInput(example)}
                  className="block w-full text-left text-xs text-text-secondary hover:text-accent-green px-3 py-1.5 rounded hover:bg-bg-hover transition-colors"
                >
                  <span className="text-accent-green mr-1">$</span>
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i}>
            {msg.role === "user" ? (
              <div className="flex items-start gap-2">
                <span className="text-accent-green text-xs flex-shrink-0 mt-0.5">$</span>
                <span className="text-sm text-text-primary">{msg.content}</span>
              </div>
            ) : (
              <div className="ml-4">
                {msg.loading && (
                  <div className="text-text-muted text-xs">
                    thinking<span className="animate-pulse">...</span>
                    <span className="ml-2 text-text-muted">{elapsed}s</span>
                  </div>
                )}
                {msg.error && (
                  <div className="text-accent-red text-xs">{msg.error}</div>
                )}
                {msg.response && (
                  <AIResponse
                    response={msg.response}
                    onOptionClick={handleOptionClick}
                    filters={filters}
                    onAddCard={onAddCard ? async (scryfallId, cardName) => {
                      await onAddCard(scryfallId, cardName);
                      // Track acceptance in conversation history
                      setConversationHistory(prev => {
                        const updated = [...prev];
                        for (let i = updated.length - 1; i >= 0; i--) {
                          if (updated[i].role === "ai" && updated[i].cards_suggested?.includes(cardName)) {
                            const accepted = updated[i].cards_accepted || [];
                            if (!accepted.includes(cardName)) {
                              updated[i] = { ...updated[i], cards_accepted: [...accepted, cardName] };
                            }
                            break;
                          }
                        }
                        return updated;
                      });
                    } : undefined}
                  />
                )}
              </div>
            )}
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      <div className="p-3 border-t border-border flex-shrink-0">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="flex items-center gap-2 flex-1">
            <span className="text-accent-green text-sm">$</span>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="input-terminal flex-1"
              placeholder="ask about your deck..."
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-primary text-xs"
          >
            {loading ? "..." : "send"}
          </button>
        </form>
      </div>
    </div>
  );
}
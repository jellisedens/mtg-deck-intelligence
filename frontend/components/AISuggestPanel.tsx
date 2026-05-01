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
}

function SuggestionCardRow({ card }: { card: CardSuggestion }) {
  const [expanded, setExpanded] = useState(false);
  const [imgError, setImgError] = useState(false);

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
            <span className="text-xxs text-text-muted ml-auto">{expanded ? "▲" : "▼"}</span>
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

function AIResponse({ response }: { response: AISuggestionResponse }) {
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
          {response.suggestions.map((card, i) => (
            <SuggestionCardRow key={`${card.card_name}-${i}`} card={card} />
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

      {/* Clarification */}
      {response.needs_clarification && response.clarification_question && (
        <div className="text-xs text-accent-yellow">
          {response.clarification_question}
        </div>
      )}
    </div>
  );
}

export default function AISuggestPanel({ deckId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage },
      { role: "ai", content: "", loading: true },
    ]);
    setLoading(true);

    try {
      const response = await aiSuggest({
        prompt: userMessage,
        deck_id: deckId,
      });

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "ai",
          content: "",
          response,
        };
        return updated;
      });
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

  return (
    <div className="panel flex flex-col h-[500px]">
      <div className="px-4 py-3 border-b border-border flex-shrink-0">
        <span className="text-xs text-text-muted font-medium uppercase tracking-wider">
          AI Assistant
        </span>
        <p className="text-xxs text-text-muted mt-0.5">
          suggest cards, find cuts, analyze strategy, or swap cards
        </p>
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
                {msg.response && <AIResponse response={msg.response} />}
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
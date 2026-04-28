"use client";

import { useState, useRef, useEffect } from "react";
import { autocompleteCards, searchCards } from "@/lib/api";
import { ScryfallCard } from "@/lib/types";

interface Props {
  onAddCard: (card: ScryfallCard) => void;
  disabled?: boolean;
}

export default function CardSearch({ onAddCard, disabled }: Props) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced autocomplete
  function handleInputChange(value: string) {
    setQuery(value);
    setSelectedIndex(-1);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (value.trim().length < 2) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const results = await autocompleteCards(value.trim());
        setSuggestions(results);
        setShowDropdown(results.length > 0);
      } catch {
        setSuggestions([]);
      }
    }, 300);
  }

  // Select a card from suggestions
  async function handleSelect(cardName: string) {
    setQuery("");
    setSuggestions([]);
    setShowDropdown(false);
    setLoading(true);

    try {
      const results = await searchCards(`!"${cardName}"`);
      if (results.length > 0) {
        onAddCard(results[0]);
      }
    } catch {
      // silently fail — card search didn't return results
    } finally {
      setLoading(false);
    }
  }

  // Keyboard navigation
  function handleKeyDown(e: React.KeyboardEvent) {
    if (!showDropdown || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) =>
        prev < suggestions.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) =>
        prev > 0 ? prev - 1 : suggestions.length - 1
      );
    } else if (e.key === "Enter" && selectedIndex >= 0) {
      e.preventDefault();
      handleSelect(suggestions[selectedIndex]);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
    }
  }

  return (
    <div ref={wrapperRef} className="relative">
      <div className="flex items-center gap-2">
        <span className="text-accent-green text-sm">$</span>
        <input
          type="text"
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
          className="input-terminal flex-1"
          placeholder="search cards..."
          disabled={disabled || loading}
        />
        {loading && (
          <span className="text-text-muted text-xs animate-pulse">
            fetching...
          </span>
        )}
      </div>

      {/* Autocomplete dropdown */}
      {showDropdown && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 z-40 panel max-h-60 overflow-y-auto">
          {suggestions.map((name, i) => (
            <button
              key={name}
              onClick={() => handleSelect(name)}
              className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                i === selectedIndex
                  ? "bg-accent-green/10 text-accent-green"
                  : "text-text-primary hover:bg-bg-hover"
              }`}
            >
              {name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
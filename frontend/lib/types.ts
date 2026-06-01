// ── Auth ──────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  is_verified: boolean;
}

// ── Cards ────────────────────────────────────────────
export interface DeckCard {
  id: string;
  scryfall_id: string;
  card_name: string;
  quantity: number;
  board: "main" | "sideboard" | "commander";
  notes: string | null;
  ai_context: {
    role: string;
    roles?: string[];
    secondary_roles: string[];
    impact_score: number | null;
    impact_reason: string | null;
    synergy_notes: string;
    is_critical: boolean;
  } | null;
}

export interface ScryfallCard {
  id: string;
  name: string;
  mana_cost: string | null;
  cmc: number;
  type_line: string;
  oracle_text: string | null;
  colors: string[];
  color_identity: string[];
  legalities: Record<string, string>;
  rarity: string;
  set: string;
  set_name: string;
  prices: {
    usd: string | null;
    usd_foil: string | null;
  };
  image_uris?: {
    small: string;
    normal: string;
    large: string;
    art_crop: string;
  };
  // Double-faced cards store images per face
  card_faces?: Array<{
    name: string;
    mana_cost: string;
    type_line: string;
    oracle_text: string;
    image_uris?: {
      small: string;
      normal: string;
      large: string;
      art_crop: string;
    };
  }>;
  power: string | null;
  toughness: string | null;
}

// ── Decks ────────────────────────────────────────────
export interface Deck {
  id: string;
  name: string;
  format: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  cards?: DeckCard[];
  preferences?: DeckPreferences;
}

export interface DeckPreferences {
  strategy_notes?: string | null;
  color_preferences?: string | null;
  card_type_preferences?: string | null;
  budget?: string | null;
  power_level?: string | null;
  other_notes?: string | null;
}

export interface CreateDeckRequest {
  name: string;
  format: string;
  description?: string;
}

export interface AddCardRequest {
    scryfall_id: string;
    card_name: string;
    quantity: number;
    board: "main" | "sideboard" | "commander";
    color_identity?: string[];
  }

// ── Analytics ────────────────────────────────────────
export interface ManaCurveEntry {
  cmc: number;
  count: number;
}

export interface ColorDistribution {
  color: string;
  count: number;
}

export interface TypeDistribution {
  type: string;
  count: number;
}

export interface DeckAnalytics {
  mana_curve: ManaCurveEntry[];
  color_distribution: ColorDistribution[];
  type_distribution: TypeDistribution[];
  average_cmc: number;
  total_cards: number;
  land_count: number;
  nonland_count: number;
  mana_base: {
    land_percentage: number;
    color_sources: Record<string, number>;
  };
  deck_identity: {
    colors: string[];
    color_names: string[];
  };
}

// ── Strategy ─────────────────────────────────────────
export interface ColorHealth {
  color: string;
  score: number;
  sources: number;
  demand: number;
  status: string;
}

export interface RoleStatus {
  role: string;
  count: number;
  target: number;
  status: string;
}

export interface StrategyProfile {
  color_health: ColorHealth[];
  role_status: RoleStatus[];
  generated_at: string;
}

// ── Simulation ───────────────────────────────────────
export interface SimulatedHand {
  cards: string[];
  land_count: number;
  nonland_count: number;
  colors_available: string[];
}

export interface HandSimulationResult {
  hands: SimulatedHand[];
  statistics: {
    avg_lands: number;
    avg_nonlands: number;
    land_distribution: Record<string, number>;
    probability_by_cmc: Record<string, number>;
  };
  simulations_run: number;
}

export interface TurnStats {
  turn: number;
  avg_lands_played: number;
  avg_spells_cast: number;
  avg_creatures_on_board: number;
  avg_power_on_board: number;
  avg_mana_available: number;
}

export interface GameSimulationResult {
  turn_stats: TurnStats[];
  simulations_run: number;
  summary: {
    avg_turn_to_full_curve: number;
    avg_total_damage_by_turn_7: number;
  };
}

// ── AI Suggestions ───────────────────────────────────
export interface CardSuggestion {
  card_name: string;
  scryfall_id: string | null;
  reasoning: string;
  category: string | null;
  priority: string | null;
  image_uri: string | null;
  mana_cost: string | null;
  type_line: string | null;
  price_usd: string | null;
}

export interface CutSuggestion {
  card_name: string;
  reasoning: string;
  impact_score: number | null;
}

export interface ClarificationOption {
  label: string;
  description?: string;
}

export interface AISuggestionResponse {
  summary: string | null;
  suggestions: CardSuggestion[];
  cuts: CutSuggestion[];
  strategy_notes: string | null;
  needs_clarification: boolean;
  clarification_question: string | null;
  clarification_options?: ClarificationOption[];
  _original_category?: string;
}

export interface AISuggestRequest {
  prompt: string;
  deck_id: string;
  conversation_context?: Array<{
    role: string;
    content: string;
    cards_suggested?: string[];
    cards_accepted?: string[];
  }>;
}

// ── Import ───────────────────────────────────────────
export interface ImportArchidektRequest {
  url: string;
  name?: string;
}

export interface ImportTextRequest {
  deck_text: string;
  name: string;
  format: string;
  description?: string;
}

// ── SSE Strategy Events ──────────────────────────────
export interface StrategySSEEvent {
  step: string;
  progress: number;
  message: string;
}
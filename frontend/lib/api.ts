import {
  AuthResponse,
  LoginRequest,
  SignupRequest,
  Deck,
  CreateDeckRequest,
  AddCardRequest,
  DeckPreferences,
  DeckAnalytics,
  StrategyProfile,
  HandSimulationResult,
  GameSimulationResult,
  AISuggestRequest,
  AISuggestionResponse,
  ImportArchidektRequest,
  ImportTextRequest,
  ScryfallCard,
} from "./types";

// ── Config ───────────────────────────────────────────
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// ── Token management ─────────────────────────────────
let token: string | null = null;

export function getToken(): string | null {
  if (token) return token;
  if (typeof window !== "undefined") {
    token = localStorage.getItem("mtg_token");
  }
  return token;
}

export function setToken(t: string) {
  token = t;
  if (typeof window !== "undefined") {
    localStorage.setItem("mtg_token", t);
  }
}

function getRefreshToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("mtg_refresh_token");
  }
  return null;
}

function setRefreshToken(t: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("mtg_refresh_token", t);
  }
}

export function clearToken() {
  token = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("mtg_token");
    localStorage.removeItem("mtg_refresh_token");
  }
}

// ── Token refresh ────────────────────────────────────
let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  // Deduplicate concurrent refresh attempts
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const rt = getRefreshToken();
    if (!rt) return false;

    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: rt }),
      });

      if (!res.ok) return false;

      const data = await res.json();
      setToken(data.access_token);
      setRefreshToken(data.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ── Base request helper ──────────────────────────────
async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const t = getToken();
  if (t) {
    headers["Authorization"] = `Bearer ${t}`;
  }

  let res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  // On 401, try refreshing the token once
  if (res.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      // Retry with new token
      headers["Authorization"] = `Bearer ${getToken()}`;
      res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
      });
    }

    if (res.status === 401) {
      clearToken();
      if (typeof window !== "undefined") {
        window.location.href = "/auth/login";
      }
      throw new Error("Unauthorized");
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

// ── Auth ─────────────────────────────────────────────
export async function login(data: LoginRequest): Promise<AuthResponse> {
  const res = await request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
  setToken(res.access_token);
  setRefreshToken(res.refresh_token);
  return res;
}

export async function signup(data: SignupRequest): Promise<AuthResponse> {
  const res = await request<AuthResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(data),
  });
  setToken(res.access_token);
  setRefreshToken(res.refresh_token);
  return res;
}

export function logout() {
  clearToken();
}

// ── Decks ────────────────────────────────────────────
export async function getDecks(): Promise<Deck[]> {
  return request<Deck[]>("/decks");
}

export async function getDeck(id: string): Promise<Deck> {
  return request<Deck>(`/decks/${id}`);
}

export async function createDeck(data: CreateDeckRequest): Promise<Deck> {
  return request<Deck>("/decks", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateDeck(
  id: string,
  data: Partial<CreateDeckRequest>
): Promise<Deck> {
  return request<Deck>(`/decks/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteDeck(id: string): Promise<void> {
  return request<void>(`/decks/${id}`, { method: "DELETE" });
}

export async function updateDeckPreferences(
  id: string,
  prefs: Partial<DeckPreferences>
): Promise<Deck> {
  return request<Deck>(`/decks/${id}/preferences`, {
    method: "PUT",
    body: JSON.stringify(prefs),
  });
}

// ── Deck Cards ───────────────────────────────────────
export async function addCard(
  deckId: string,
  data: AddCardRequest
): Promise<Deck> {
  return request<Deck>(`/decks/${deckId}/cards`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateCard(
  deckId: string,
  cardId: string,
    data: { quantity?: number; board?: string; notes?: string }
): Promise<Deck> {
  return request<Deck>(`/decks/${deckId}/cards/${cardId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function removeCard(
  deckId: string,
  cardId: string
): Promise<void> {
  return request<void>(`/decks/${deckId}/cards/${cardId}`, {
    method: "DELETE",
  });
}

// ── Import ───────────────────────────────────────────
export async function importArchidekt(
  data: ImportArchidektRequest
): Promise<Deck> {
  const res = await request<{ deck_id: string; name: string; format: string; cards_imported: number }>(
    "/decks/import/archidekt",
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
  // Fetch the full deck after import
  return getDeck(res.deck_id);
}

export async function importText(data: ImportTextRequest): Promise<Deck> {
  const res = await request<{ deck_id: string; name: string; format: string; cards_imported: number }>(
    "/decks/import/text",
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
  // Fetch the full deck after import
  return getDeck(res.deck_id);
}

// ── Analytics ────────────────────────────────────────
export async function getAnalytics(deckId: string): Promise<DeckAnalytics> {
  return request<DeckAnalytics>(`/decks/${deckId}/analytics`);
}

// ── Strategy ─────────────────────────────────────────
export async function generateStrategy(
  deckId: string
): Promise<StrategyProfile> {
  return request<StrategyProfile>(`/decks/${deckId}/strategy`, {
    method: "POST",
  });
}

export async function getStrategy(
  deckId: string
): Promise<Record<string, unknown> | null> {
  try {
    return await request<Record<string, unknown>>(`/decks/${deckId}/strategy`);
  } catch {
    return null;
  }
}

// SSE stream for strategy generation progress
export function streamStrategy(
  deckId: string,
  onEvent: (event: { step: string; progress: number; message: string }) => void,
  onDone: () => void,
  onError: (err: string) => void
): () => void {
  const t = getToken();
  const url = `${API_BASE}/decks/${deckId}/strategy/stream?token=${t}`;
  const source = new EventSource(url);

  source.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.step === "complete") {
        source.close();
        onDone();
      } else if (data.step === "error") {
        source.close();
        onError(data.message);
      } else {
        onEvent(data);
      }
    } catch {
      // ignore malformed events
    }
  };

  source.onerror = () => {
    source.close();
    onError("Connection lost");
  };

  // Return cleanup function
  return () => source.close();
}

// ── Simulation ───────────────────────────────────────
export async function simulateHand(
  deckId: string,
  count?: number
): Promise<HandSimulationResult> {
  const params = count ? `?simulations=${count}` : "";
  return request<HandSimulationResult>(
    `/decks/${deckId}/simulate/hand${params}`,
    { method: "POST" }
  );
}

export async function simulateGame(
  deckId: string,
  count?: number
): Promise<Record<string, unknown>> {
  const params = count ? `?n_games=${count}` : "";
  return request<Record<string, unknown>>(
    `/decks/${deckId}/simulate/game${params}`,
    { method: "POST" }
  );
}

// ── AI Suggestions ───────────────────────────────────
export async function aiSuggest(
  data: AISuggestRequest
): Promise<AISuggestionResponse> {
  return request<AISuggestionResponse>("/ai/suggest", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Scryfall ─────────────────────────────────────────
export async function searchCards(query: string): Promise<ScryfallCard[]> {
  const res = await request<{ data: ScryfallCard[] }>(
    `/scryfall/search?q=${encodeURIComponent(query)}`
  );
  return res.data || [];
}

export async function autocompleteCards(
  query: string
): Promise<string[]> {
  const res = await request<{ data: string[] }>(
    `/scryfall/autocomplete?q=${encodeURIComponent(query)}`
  );
  return res.data || [];
}

export async function getCard(scryfallId: string): Promise<ScryfallCard> {
  return request<ScryfallCard>(`/scryfall/card/${scryfallId}`);
}


export async function getCardCollection(
  scryfallIds: string[]
): Promise<ScryfallCard[]> {
  const identifiers = scryfallIds.map((id) => ({ id }));
  const res = await request<{ data: ScryfallCard[] }>("/scryfall/collection", {
    method: "POST",
    body: JSON.stringify({ identifiers }),
  });
  return res.data || [];
}
# MTG Deck Intelligence — Testing Checklist

## Authentication & Security

### Rate Limiting
- [ ] Rapidly click "generate strategy" multiple times — should get "Rate limit exceeded"
- [ ] Rapidly click AI suggest multiple times — should get rate limit message
- [ ] Rapid login attempts — should be throttled after 10

### JWT Refresh Tokens
- [ ] Log in, use app for 30+ minutes — should stay logged in
- [ ] Token refresh should happen silently (check Network tab for /auth/refresh calls)

### Email Verification
- [ ] Sign up with new email — verification email arrives (check spam)
- [ ] Click verify link — shows "Verified!" page
- [ ] Unverified user sees amber banner on deck list and deck builder
- [ ] Unverified user blocked from: AI suggest, simulation, strategy generation
- [ ] "Resend verification email" button sends another email
- [ ] After verifying, banner disappears on next login or token refresh

## Deck Management

### Create & Import
- [ ] Create new empty deck — works, shows empty state
- [ ] Import from Archidekt URL — deck imports with all cards
- [ ] Import text list — deck creates with correct cards
- [ ] Delete deck — requires confirm click, removes from list

### Deck Export
- [ ] Click "export" — modal opens with deck list grouped by type
- [ ] "text (1x)" format shows `1x Card Name`
- [ ] "MTGO" format shows `1 Card Name`
- [ ] Commander section appears at top
- [ ] Sideboard section appears separately
- [ ] "Copy to clipboard" works — paste to confirm
- [ ] Card count in header matches deck

### Card Sorting
- [ ] "type" — groups by card type (default, matches previous behavior)
- [ ] "name" — flat alphabetical list
- [ ] "cmc" — lowest mana cost first
- [ ] "price" — most expensive first
- [ ] "impact" — highest AI impact score first (needs strategy profile)

### Card Operations
- [ ] Add card via search — appears in deck list
- [ ] Update quantity with +/- buttons
- [ ] Remove card — disappears from list
- [ ] Move card between main/sideboard/commander
- [ ] Add card notes — persists after page reload
- [ ] Auto-tag roles — assigns roles to untagged cards

## Strategy & AI

### Strategy Profile
- [ ] Generate on empty deck — button disabled, shows helper text
- [ ] Generate on deck with cards — progress stream works, completes
- [ ] Profile displays after generation (commander role, strategy, etc.)
- [ ] Regenerate — replaces old profile
- [ ] Strategy only fetched once on page load (check Network tab)

### AI Suggestions
- [ ] Type a prompt — get card suggestions with images
- [ ] "Add to deck" button on suggestions — card appears in deck
- [ ] Conversation context maintained across multiple prompts
- [ ] Clarification options appear when query is ambiguous

## Simulation

### Hand Simulator
- [ ] Draw hand — shows 7 card images
- [ ] Mulligan — redraws with fewer cards
- [ ] Session stats track across multiple draws
- [ ] Land distribution shown

### Game Simulator
- [ ] Run simulation with default settings (500 games, 10 turns)
- [ ] All tabs display data: insights, mana, colors, draws, chart
- [ ] Mana tab — no `.toFixed()` errors, all values display
- [ ] Custom tracking: card types, commander castability
- [ ] Results render on both local and production

### Deck Versioning
- [ ] Save version — creates snapshot
- [ ] View version list
- [ ] Compare versions — shows card diffs

## Mobile / Responsive

- [ ] Header buttons wrap to second line (don't overlap)
- [ ] Deck name truncates if too long
- [ ] Card search usable on mobile
- [ ] Hand simulator modal fits mobile screen
- [ ] Game simulator modal fits mobile screen
- [ ] Export modal fits mobile screen
- [ ] Sort buttons accessible on small screens
- [ ] Navigation works on mobile

## Error Handling

- [ ] 403 verification error shows readable message
- [ ] 429 rate limit shows friendly message
- [ ] Network failure shows error, doesn't crash
- [ ] No `[object Object]` in any error messages
- [ ] Strategy generation failure shows error, not "connection lost"

## Production-Specific

- [ ] Frontend loads at production URL
- [ ] Backend API responds at production URL
- [ ] CORS working — no blocked requests
- [ ] Login works on production
- [ ] Strategy generates and saves on production
- [ ] Simulation runs and displays on production
- [ ] Hard refresh (Ctrl+Shift+R) loads latest version after deploy
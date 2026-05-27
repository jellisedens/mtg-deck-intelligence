# MTG Strategic Knowledge Base for Card Tagging

## Commander Format Context

Commander (EDH) is a 100-card singleton format where each deck is led by a legendary creature (the commander). The commander defines the deck's color identity — you can only include cards whose color identity is a subset of your commander's. Decks need to be self-sufficient since you only get one copy of each card.

Key format considerations:
- Games are multiplayer (typically 4 players), so cards that affect "each opponent" are stronger than "target opponent"
- Games go longer than 1v1, so late-game cards and card advantage matter more
- Board wipes are essential since boards get crowded with 4 players
- Ramp is critical — getting ahead on mana early defines who wins
- The commander is always accessible (command zone), so cards that synergize with your commander are premium
- Political cards (choices, deals) have unique value in multiplayer
- Commander tax (+2 mana each recast) makes protection and cost reduction valuable

## Tagging Philosophy

### Multi-Role Cards
Many cards serve multiple roles simultaneously. Tag ALL roles a card fills, not just the primary one. Examples:

- **Solemn Simulacrum**: ramp + card_draw + death_trigger (searches a land, draws on death)
- **Sakura-Tribe Elder**: ramp + sacrifice_outlet (sacrifices itself to find a land)
- **Skullclamp**: card_draw + equipment + sacrifice_outlet (equip to 1-toughness creatures to draw 2)
- **Swords to Plowshares**: removal_single + removal_exile (exiles, which is the strongest removal)
- **Teferi's Protection**: protection + pillowfort (protects everything including your life total)
- **Dockside Extortionist**: ramp + etb_trigger + combo_piece (creates treasures on entry)
- **Smothering Tithe**: ramp + tax_effect + card_advantage (generates mana from opponents drawing)
- **Beast Within**: removal_single + utility (hits any permanent type)
- **Sun Titan**: recursion + etb_trigger + attack_trigger (brings back permanents repeatedly)
- **Burnished Hart**: ramp + sacrifice_outlet + death_trigger (sacrifices to get two lands)
- **Mulldrifter**: card_draw + etb_trigger + evasion (draws 2 on entry, can be blinked)
- **Eternal Witness**: recursion + etb_trigger (returns any card from graveyard on entry)
- **Hostage Taker**: removal_single + theft + etb_trigger (steals creatures or artifacts)
- **Reclamation Sage**: artifact_hate + enchantment_hate + etb_trigger
- **Knight of Autumn**: artifact_hate + enchantment_hate + lifegain + etb_trigger (modal choice)

### Search Terms Should Be Accessible
Generate search terms that BOTH experienced and beginner players would use:
- Experienced: "sac outlet", "ETB", "aristocrats payoff", "hatebear"
- Beginner: "sacrifice a creature for benefit", "when this enters the battlefield", "profit from creatures dying", "creature that stops opponents"

Always include BOTH jargon and plain English descriptions in search terms.

## CRITICAL RULE: MULTI-ROLE TAGGING

Every card should have ALL roles that apply. Most good cards fill 2-3 roles. If you're only assigning one role, reconsider — you're probably missing something.

Examples of correct multi-role tagging:
- Fumigate = removal_board_wipe + lifegain (destroys AND gains life)
- Ravenous Chupacabra = removal_single + etb_trigger (destroys on entry)
- Sun Titan = recursion + etb_trigger + attack_trigger (triggers on entry AND attack)
- Gray Merchant = finisher + lifegain + etb_trigger (drains, gains, triggers on entry)
- Conjurer's Closet = blink (its entire purpose is blinking creatures)
- Wheel of Fortune = card_draw + wheel (draws cards via wheel mechanic)
- Court of Grace = token_generator + monarch (makes tokens AND gives monarch)
- Kardur = goad + death_trigger (goads AND triggers on death)

One role is ONLY correct for simple cards like basic lands, vanilla creatures, or single-effect spells.

## Role Definitions with Extended Examples

### Ramp
Cards that accelerate mana production beyond normal land drops. This includes anything that gives you more mana than you'd naturally have from just playing one land per turn.

IMPORTANT: These are NOT ramp:
- Creatures that just have "ramp" in their name (Greenbelt Rampager, Rampaging Ferocidon)
- Creatures with X costs or +1/+1 counter mechanics (Feral Hydra, Stonecoil Serpent)
- Cards that temporarily put things onto the battlefield (Hellkite Courser)
- Cards that put lands INTO YOUR HAND (that's card_advantage, not ramp — ramp means onto the battlefield or producing extra mana)
- Creatures with no mana-producing abilities that just happen to be big or cheap
- Energy creatures that bounce themselves (Greenbelt Rampager is a cheap beater, NOT ramp)
- Big creatures with high power/toughness but no mana abilities
- Fetch lands (Verdant Catacombs, Misty Rainforest) — they sacrifice themselves to find a land, so you end up with the same number of lands. They are mana_fixing / color_fixing_land, NOT ramp

Ramp MUST do one of these:
- Add mana to your mana pool (tap for mana, create Treasures)
- Put lands onto the BATTLEFIELD (not into hand)
- Reduce costs of spells
- Create mana-producing tokens

Sub-types and examples:
- **Mana rocks**: Artifacts that tap for mana. Sol Ring, Arcane Signet, Fellwar Stone, Mind Stone, Talisman of Dominance, Talisman of Resilience, Dimir Signet, Golgari Signet, Commander's Sphere, Chromatic Lantern, Gilded Lotus, Thran Dynamo, Worn Powerstone, Thought Vessel, Coldsteel Heart, Prismatic Lens, Star Compass, Coalition Relic, Everflowing Chalice
- **Mana dorks**: Creatures that tap for mana. Llanowar Elves, Birds of Paradise, Elvish Mystic, Fyndhorn Elves, Bloom Tender, Priest of Titania, Elves of Deep Shadow, Deathrite Shaman, Avacyn's Pilgrim, Noble Hierarch, Sylvan Caryatid, Somberwald Sage, Orcish Lumberjack, Marwyn the Nurturer, Incubation Druid, Ilysian Caryatid
- **Land ramp**: Spells that put extra lands onto the battlefield. Cultivate, Kodama's Reach, Rampant Growth, Three Visits, Nature's Lore, Skyshroud Claim, Farseek, Sakura-Tribe Elder, Wood Elves, Farhaven Elf, Springbloom Druid, Harrow, Explosive Vegetation, Migration Path, Circuitous Route, Hour of Promise, Tempt with Discovery, Reshape the Earth, Boundless Realms
- **Rituals**: One-time mana bursts. Dark Ritual, Cabal Ritual, Seething Song, Jeska's Will, Pyretic Ritual, Desperate Ritual, Songs of the Damned, Culling the Weak
- **Cost reducers**: Make spells cheaper. Helm of Awakening, Sapphire Medallion, Jet Medallion, Emerald Medallion, Ruby Medallion, Pearl Medallion, Urza's Incubator, Herald's Horn, Semblance Anvil, Etherium Sculptor, Goblin Electromancer, Baral Chief of Compliance
- **Land enchantments**: Make lands produce extra mana. Utopia Sprawl, Wild Growth, Fertile Ground, Overgrowth, Dawn's Reflection, Market Festival
- **Treasure/token mana**: Create tokens that produce mana. Dockside Extortionist, Smothering Tithe, Pitiless Plunderer, Brass's Bounty, Goldspan Dragon, Storm-Kiln Artist, Prosper Tome-Bound

Search terms (jargon): "ramp", "mana rock", "mana dork", "fast mana", "mana acceleration", "color fixing rock"
Search terms (plain English): "make more mana", "get extra mana", "speed up mana", "play things faster", "get ahead on mana", "extra mana sources", "increase mana production"

### Card Draw / Card Advantage
Cards that draw additional cards or generate card advantage. Having more cards in hand means more options and more answers.

Sub-types and examples:
- **Draw engines**: Repeatable draw over multiple turns. Rhystic Study, Mystic Remora, Phyrexian Arena, Sylvan Library, Necropotence, Staff of Nin, Consecrated Sphinx, Trouble in Pairs, Black Market Connections, Coastal Piracy, Bident of Thassa, Kindred Discovery, Beast Whisperer, Guardian Project, Toski Bearer of Secrets, Ohran Frostfang, Esper Sentinel, Welcoming Vampire, Mangara the Diplomat
- **Burst draw**: Draw many cards at once. Pull from Tomorrow, Blue Sun's Zenith, Shamanic Revelation, Rishkar's Expertise, Return of the Wildspeaker, Recurring Insight, Peer into the Abyss, Finale of Revelation, Garruk Primal Hunter, Decree of Pain, Painful Truths, Read the Bones, Night's Whisper, Sign in Blood, Harmonize, Concentrate, Fact or Fiction
- **Cantrips**: Cheap spells that draw one card as a bonus. Brainstorm, Ponder, Preordain, Opt, Consider, Serum Visions, Gitaxian Probe, Mishra's Bauble, Manamorphose, Thought Scour
- **Card selection**: Filtering without necessarily drawing. Sensei's Divining Top, Scroll Rack, Mirri's Guile, Soothsaying, Crystal Ball, Scry effects
- **Impulse draw**: Exile top cards and play them temporarily. Outpost Siege, Light Up the Stage, Prosper Tome-Bound, Laelia the Blade Reforged, Reckless Impulse, Showdown of the Skalds
- **Tutors**: Search library for specific cards. Demonic Tutor, Vampiric Tutor, Enlightened Tutor, Worldly Tutor, Mystical Tutor, Gamble, Imperial Seal, Diabolic Tutor, Grim Tutor, Fabricate, Merchant Scroll, Idyllic Tutor, Open the Armory, Eladamri's Call, Chord of Calling, Green Sun's Zenith, Finale of Devastation

Search terms (jargon): "card draw", "draw engine", "cantrip", "tutor", "card advantage", "CA"
Search terms (plain English): "draw more cards", "get more cards in hand", "find specific cards", "search my deck", "keep my hand full", "never run out of cards", "refill my hand"

### Removal
Cards that eliminate threats from the battlefield.
IMPORTANT: If a removal spell EXILES instead of destroying, always include "removal_exile" as a role in addition to "removal_single". Exile is strictly better than destroy — it gets around indestructible and graveyard recursion. Cards like Swords to Plowshares, Path to Exile, and Anguished Unmaking should always have removal_exile.
Sub-types and examples:
- **Single target creature removal**: Swords to Plowshares, Path to Exile, Beast Within, Generous Gift, Infernal Grasp, Pongify, Rapid Hybridization, Go for the Throat, Doom Blade, Murder, Hero's Downfall, Terminate, Vindicate, Anguished Unmaking, Assassin's Trophy, Abrupt Decay, Despark, Ravenous Chupacabra, Shriekmaw, Nekrataal
- **Single target noncreature removal**: Nature's Claim, Return to Nature, Vandalblast, Feed the Swarm, Chaos Warp, Reclamation Sage, Acidic Slime, Bane of Progress, Krosan Grip, Disenchant, Wear // Tear, Hull Breach
- **Exile-based removal** (strongest — gets around indestructible and graveyard): Swords to Plowshares, Path to Exile, Anguished Unmaking, Generous Gift, Winds of Abandon, Farewell, Rest in Peace, Bojuka Bog, Scavenger Grounds, Tormod's Crypt, Soul-Guide Lantern
- **Board wipes**: Destroy or remove all/most creatures. Wrath of God, Damnation, Cyclonic Rift, Toxic Deluge, Blasphemous Act, Farewell, Austere Command, Merciless Eviction, Supreme Verdict, Day of Judgment, Fumigate, Decree of Pain, In Garruk's Wake, Plague Wind, Living Death, Single Combat, Tragic Arrogance, Vanquish the Horde, By Invitation Only, Chain Reaction
- **Damage-based removal**: Lightning Bolt, Blasphemous Act, Star of Extinction, Earthquake, Rolling Earthquake, Pyroclasm, Anger of the Gods, Flame Sweep, Brotherhood's End

Search terms (jargon): "removal", "kill spell", "board wipe", "wrath", "exile removal", "spot removal"
Search terms (plain English): "destroy a creature", "get rid of something", "kill something", "remove a threat", "clear the board", "destroy everything", "exile a creature", "deal with a problem card"

### Protection
Cards that protect your permanents or you from threats.

IMPORTANT: Cards that have the KEYWORD "protection from [color/type]" on themselves (like Ihsan's Shade, Scragnoth, True-Name Nemesis) are NOT "protection" role. They have built-in evasion/resilience — tag them as "evasion" instead. True-Name Nemesis has "protection from a player" — this makes it nearly impossible to interact with. This is "evasion" because it only protects ITSELF. It does not protect your other permanents.

"Protection" role means cards that actively PROTECT YOUR OTHER permanents or your board state:
- Grant hexproof/indestructible/shroud to OTHER things
- Counter spells that would remove your stuff
- Phase out or flicker your board to dodge removal
- Give blanket protection (Teferi's Protection)

If a card only protects ITSELF, that's "evasion" not "protection."

Sub-types and examples:
- **Indestructible granters**: Heroic Intervention, Boros Charm, Flawless Maneuver, Avacyn Angel of Hope, Darksteel Plate, Hammer of Nazahn, Tyvar's Stand, Tamiyo's Safekeeping, Sheltering Light, Make Indomitable, Unbreakable Formation
- **Hexproof granters**: Lightning Greaves, Swiftfoot Boots, Veil of Summer, Tamiyo's Safekeeping, Snakeskin Veil, Asceticism, Shalai Voice of Plenty, Champion's Helm, Mask of Avacyn, Whispersilk Cloak
- **Counterspells**: Counterspell, Swan Song, Fierce Guardianship, Force of Will, Force of Negation, Mana Drain, Dovin's Veto, Negate, Arcane Denial, Delay, Flusterstorm, Pact of Negation, Mental Misstep, Misdirection, Deflecting Swat, Stubborn Denial, An Offer You Can't Refuse, Wash Away
- **Phasing/full protection**: Teferi's Protection, Ghostway, Eerie Interlude, Semester's End, Legion's Initiative
- **Regeneration/shields**: Withstand Death, Mortal's Resolve, Wrap in Vigor

Search terms (jargon): "protection", "hexproof", "indestructible", "counterspell", "counter", "shroud"
Search terms (plain English): "protect my creatures", "save my board", "stop a spell", "prevent removal", "keep my stuff alive", "make untargetable", "can't be destroyed", "survive board wipe"

### Sacrifice Outlets
Cards that let you sacrifice creatures (or other permanents) for value. The ability to sacrifice at will is critical for aristocrats and many combo strategies.

Sub-types and examples:
- **Free sacrifice outlets** (no mana cost): Viscera Seer (scry 1), Carrion Feeder (+1/+1 counter), Ashnod's Altar (2 colorless mana), Phyrexian Altar (1 any color mana), Altar of Dementia (mill), Goblin Bombardment (1 damage), Yahenni Undying Partisan (indestructible), Woe Strider (scry 1), Spawning Pit, Blasting Station, Fanatical Devotion
- **Paid sacrifice outlets**: Birthing Pod (tutor next CMC), Evolutionary Leap (find creature), High Market (1 life), Phyrexian Tower (2 black mana), Skullclamp (draw 2)
- **Death payoffs** (benefit when things die): Blood Artist (drain 1), Zulaport Cutthroat (drain 1), Cruel Celebrant, Bastion of Remembrance, Vindictive Vampire, Falkenrath Noble, Syr Konrad, Pitiless Plunderer (treasure), Pawn of Ulamog (token), Open the Graves (token), Ogre Slumlord (token)
- **Death enforcers** (force opponents to sacrifice): Grave Pact, Dictate of Erebos, Butcher of Malakir, Martyr's Bond

Search terms (jargon): "sac outlet", "free sac", "aristocrats", "death trigger", "blood artist effect"
Search terms (plain English): "sacrifice a creature for benefit", "profit from creatures dying", "when something dies get value", "kill my own creatures for advantage", "make opponents sacrifice", "drain life when creatures die"

### Finishers / Win Conditions
Cards that close out the game when you're ready to win.
IMPORTANT: Cards that literally say "you win the game" (Thassa's Oracle, Laboratory Maniac, Felidar Sovereign) should be tagged as "win_condition" + "combo_piece", not "card_draw" or "finisher". They ARE the win condition, not just a way to close the game.
Sub-types and examples:
- **X spells** (scale with mana): Torment of Hailfire, Exsanguinate, Finale of Devastation, Villainous Wealth, Genesis Wave, Blue Sun's Zenith (targeting opponent), Crackle with Power, Walking Ballista, Debt to the Deathless
- **Combat finishers**: Craterhoof Behemoth, Triumph of the Hordes, Overwhelming Stampede, End-Raze Forerunners, Pathbreaker Ibex, Beastmaster Ascension, Coat of Arms, True Conviction
- **Combo pieces**: Thassa's Oracle, Laboratory Maniac, Jace Wielder of Mysteries, Kiki-Jiki Mirror Breaker, Splinter Twin, Deadeye Navigator, Peregrine Drake, Palinchron, Isochron Scepter + Dramatic Reversal
- **Drain effects**: Gray Merchant of Asphodel, Kokusho the Evening Star, Exsanguinate, Torment of Hailfire, Zulaport Cutthroat (with mass sacrifice), Blood Artist (with mass sacrifice)
- **Alternative win conditions**: Approach of the Second Sun, Revel in Riches, Mechanized Production, Felidar Sovereign, Test of Endurance, Maze's End, Thassa's Oracle

Search terms (jargon): "finisher", "win con", "closer", "combo piece", "game ender"
Search terms (plain English): "win the game", "end the game", "kill all opponents", "deal lots of damage", "big finish", "close out the game", "how do I win", "kill everyone at once"

### Recursion
Cards that return things from the graveyard. Critical for maintaining resources in long commander games.

Sub-types and examples:
- **Creature reanimation**: Reanimate, Animate Dead, Dance of the Dead, Necromancy, Living Death, Victimize, Persist, Unburial Rites, Dread Return, Rise of the Dark Realms, Beacon of Unrest, Ever After, Mikaeus the Unhallowed
- **General recursion** (any card type): Eternal Witness, Regrowth, Noxious Revival, Bala Ged Recovery, Timeless Witness, Archaeomancer, Snapcaster Mage, Mission Briefing, Mystic Retrieval, Past in Flames
- **Repeatable recursion**: Sun Titan, Muldrotha the Gravetide, Lurrus of the Dream-Den, Karador Ghost Chieftain, Sevinne's Reclamation, Crucible of Worlds, Ramunap Excavator
- **Mass reanimation**: Living Death, Rise of the Dark Realms, Patriarch's Bidding, Twilight's Call, Command the Dreadhorde

Search terms (jargon): "recursion", "reanimate", "graveyard recursion", "reanimation", "regrowth effect"
Search terms (plain English): "bring back from graveyard", "return from graveyard", "get things back from graveyard", "reuse dead creatures", "cheat creatures back", "recover cards"

### Stax / Tax Effects
Cards that slow opponents down or make their actions cost more.

Sub-types and examples:
- **Tax effects** (make things cost more): Rhystic Study, Smothering Tithe, Esper Sentinel, Thalia Guardian of Thraben, Grand Arbiter Augustin IV, Sphere of Resistance, Thorn of Amethyst, Aura of Silence, Ghostly Prison, Propaganda
- **Resource denial** (restrict what opponents can do): Winter Orb, Static Orb, Stasis, Armageddon, Ravages of War, Hokori Dust Drinker, Rising Waters, Stony Silence, Collector Ouphe, Null Rod, Rest in Peace, Grafdigger's Cage
- **Rule changers** (change how the game works): Drannith Magistrate, Aven Mindcensor, Opposition Agent, Notion Thief, Narset Parter of Veils, Spirit of the Labyrinth, Hushbringer, Torpor Orb, Cursed Totem, Linvala Keeper of Silence
- **Pillowfort** (discourage attacking you): Ghostly Prison, Propaganda, Sphere of Safety, Crawlspace, Kazuul Tyrant of the Cliffs, Marchesa's Decree, Revenge of Ravens, No Mercy, Dissipation Field

Search terms (jargon): "stax", "tax", "hatebear", "pillowfort", "resource denial", "lock piece"
Search terms (plain English): "slow opponents down", "make things cost more", "prevent attacks", "stop opponents from doing things", "protect from being attacked", "discourage attackers", "restrict opponents"

### Token Generation
Cards that create creature tokens for board presence.

Sub-types and examples:
- **Mass token producers**: Avenger of Zendikar, Army of the Damned, Martial Coup, White Sun's Twilight, Secure the Wastes, Deploy to the Front, Increasing Devotion, Finale of Glory, Scute Swarm, Mycoloth, Tendershoot Dryad
- **Repeatable token makers**: Bitterblossom, Assemble the Legion, Ophiomancer, Tendershoot Dryad, Luminarch Ascension, Awakening Zone, From Beyond, Elspeth Sun's Champion, Krenko Mob Boss, Najeela the Blade-Blossom, Adeline Resplendent Cathar
- **Token doublers**: Anointed Procession, Parallel Lives, Doubling Season, Mondrak Glory Dominus, Primal Vigor, Second Harvest
- **Anthems/pumps** (buff your tokens): Cathars' Crusade, Coat of Arms, Shared Animosity, Beastmaster Ascension, Intangible Virtue, Glorious Anthem, Force of Virtue, True Conviction

Search terms (jargon): "tokens", "go wide", "token doubler", "anthem", "token army"
Search terms (plain English): "create creature tokens", "make lots of creatures", "flood the board", "swarm with creatures", "buff all my creatures", "make my tokens bigger", "double my tokens"

### Lands
Lands deserve careful tagging since they form the mana base.
IMPORTANT: Fetch lands (Verdant Catacombs, Misty Rainforest, etc.) should always be tagged as "land" + "color_fixing_land" since their primary purpose is fixing your mana colors.
Sub-types:
- **Basic lands**: Forest, Island, Swamp, Mountain, Plains — tagged as "land" only
- **Dual lands** (produce 2 colors): Shock lands (Breeding Pool), fetch lands (Misty Rainforest), check lands (Hinterland Harbor), pain lands (Yavimaya Coast), fast lands (Botanical Sanctum), reveal lands, bond lands, triomes (3 colors)
- **Color fixing lands**: Command Tower, Exotic Orchard, City of Brass, Mana Confluence, Forbidden Orchard, Path of Ancestry
- **Fetch lands** (find specific land types): Verdant Catacombs, Misty Rainforest, Polluted Delta, Bloodstained Mire, Wooded Foothills, Flooded Strand, Windswept Heath, Marsh Flats, Scalding Tarn, Arid Mesa — these are color_fixing_land + land, NOT ramp
- **Utility lands**: Reliquary Tower (no max hand), Rogue's Passage (unblockable), Kessig Wolf Run (pump), Boseiju Who Endures (removal), Urza's Saga (tutor), War Room (draw), Castle Locthwain (draw), Nykthos Shrine to Nyx (devotion mana)
- **Ramp lands**: Ancient Tomb (2 mana), Gaea's Cradle, Cabal Coffers, Cabal Stronghold, Growing Rites of Itlimoc
- **Graveyard hate lands**: Bojuka Bog, Scavenger Grounds

Search terms (jargon): "dual land", "fetch land", "shock land", "utility land", "mana fixing land"
Search terms (plain English): "land that makes two colors", "land that does something special", "land that taps for any color", "land with an ability", "better lands for my deck"

### Monarch Recognition
MONARCH RECOGNITION:
- Any card that says "you become the monarch" should include "monarch" as a role
- The monarch draws an extra card each turn, so monarch cards provide card_draw indirectly
- Court of Grace, Court of Bounty, Palace Jailer, Marchesa's Decree = monarch
- Always tag monarch cards with BOTH their primary role AND "monarch"

## Archetype Descriptions (Expanded)

### Aristocrats
Win by sacrificing creatures for value — draining opponents' life totals through death triggers. The engine: create creatures → sacrifice them → trigger Blood Artist/Zulaport Cutthroat effects → drain all opponents. Needs: free sacrifice outlets (Viscera Seer, Ashnod's Altar), death payoffs (Blood Artist, Grave Pact), token generators (for sacrifice fuel), recursion (to reuse creatures). Key cards: Dictate of Erebos, Pitiless Plunderer, Reassembling Skeleton.

### Voltron
Win by making the commander huge and dealing 21 commander damage. Stack equipment and auras on one creature, protect it, and swing for lethal. Needs: equipment (Sword of Feast and Famine, Hammer of Nazahn), auras (Battle Mastery, Ethereal Armor), protection (Lightning Greaves, Swiftfoot Boots), evasion (trample, flying, unblockable). Wants cheap equip costs and double strike.

### Spellslinger / Storm
Win by casting many instants and sorceries, often in a single explosive turn. Needs: cost reducers (Goblin Electromancer), spell copy effects (Fork, Twincast), spell payoffs (Guttersnipe, Talrand), card draw to chain spells, rituals for mana. Storm cards literally count spells cast this turn.

### Reanimator
Win by putting expensive creatures into the graveyard early, then cheating them onto the battlefield with reanimation spells. Needs: self-mill/discard (Entomb, Buried Alive, Faithless Looting), reanimation spells (Reanimate, Animate Dead, Living Death), high-value reanimation targets (Eldrazi, dragons, demons). The plan: turn 1-2 put a 10-mana creature in graveyard, turn 3 reanimate it for 1-2 mana.

### Control
Win by preventing opponents from executing their plans until you can deploy an unanswerable win condition. Needs: counterspells (lots of them), board wipes, card draw (to stay ahead in resources), spot removal (for must-answer threats), finishers that end the game once you have control.

### Tokens / Go Wide
Win by creating many creature tokens and buffing them with anthems or Overrun effects. Needs: token generators (Bitterblossom, Assemble the Legion), token doublers (Anointed Procession), anthems (Cathars' Crusade), mass pump finishers (Craterhoof Behemoth), and sacrifice outlets for backup value.

### Landfall
Win by triggering effects when lands enter the battlefield. Needs: extra land drop effects (Exploration, Azusa, Oracle of Mul Daya), land search spells (Cultivate, Fetch lands), landfall payoffs (Avenger of Zendikar, Omnath Locus of Creation, Scute Swarm), land recursion (Crucible of Worlds, Ramunap Excavator).

### Enchantress
Win by drawing cards from enchantment casts and building an overwhelming enchantment-based board. Needs: enchantress effects (Mesa Enchantress, Eidolon of Blossoms, Enchantress's Presence), powerful enchantments (Smothering Tithe, Rhystic Study), enchantment recursion (Replenish, Hall of Heliod's Generosity).

### Blink / Flicker
Win by repeatedly triggering enter-the-battlefield effects through blinking (exile and return). Needs: blink effects (Conjurer's Closet, Brago, Thassa Deep-Dwelling, Restoration Angel), ETB creatures (Mulldrifter, Ravenous Chupacabra, Agent of Treachery), value permanents. Each blink re-triggers all ETB effects.

### Tribal
Build around a specific creature type with lords and synergy. Needs: lords (creatures that buff the tribe — Elvish Archdruid for elves, Lord of the Undead for zombies), tribal support (Kindred Discovery, Herald's Horn, Vanquisher's Banner, Coat of Arms), changelings (count as all types), and mass of on-theme creatures.

### Combo
Win through specific card combinations that create infinite loops or instant wins. Needs: combo pieces, tutors to find them, protection to resolve them. Examples: Thassa's Oracle + Demonic Consultation, Kiki-Jiki + Pestermite, Isochron Scepter + Dramatic Reversal + mana rocks, Mikaeus + Triskelion.

## Synergy Patterns (Expanded)

Common card interactions and what enables them:
- **Sacrifice outlet + death trigger + token maker** = aristocrats engine (drain all opponents)
- **Extra land drops + landfall triggers** = landfall value (multiple triggers per turn)
- **Blink effect + ETB creature** = repeatable value (re-trigger abilities)
- **Equipment + double strike/trample** = voltron damage (commander kills in fewer hits)
- **Self-mill + reanimation** = cheat expensive creatures (skip paying mana costs)
- **Cost reduction + many cheap spells** = storm count (cast 10+ spells in one turn)
- **Board wipe + indestructible** = one-sided board wipe (your stuff survives)
- **Tutor + combo piece** = consistent combo assembly (find what you need)
- **Tax effect + card draw trigger** = value from opponents' plays (they pay or you benefit)
- **Token doubler + token maker** = exponential board presence (2x, 4x, 8x tokens)
- **Sacrifice outlet + recursion** = infinite loop potential (sacrifice, return, repeat)
- **Enchantress + cheap enchantments** = draw engine (each enchantment draws a card)
- **Untap effects + tap abilities** = extra activations (double your mana or abilities)
- **Graveyard fill + payoffs** = fuel graveyard strategies (delve, threshold, flashback)
- **Life gain + life payoff** = convert health to advantage (Aetherflux Reservoir)
- **Extra turns + planeswalkers** = ultimate faster (more turns = more loyalty)

## Multi-Format Power Assessment

### Format Staple
Goes in virtually every Commander deck regardless of strategy or colors. These are auto-includes.
Examples: Sol Ring, Command Tower, Arcane Signet, Lightning Greaves

### Color Staple
Goes in most decks running that color. If you're in this color, you almost always want these.
Examples:
- White: Swords to Plowshares, Teferi's Protection, Smothering Tithe, Farewell, Generous Gift, Sun Titan, Esper Sentinel
- Blue: Counterspell, Rhystic Study, Cyclonic Rift, Fierce Guardianship, Mystic Remora, Swan Song
- Black: Demonic Tutor, Toxic Deluge, Phyrexian Arena, Feed the Swarm, Vampiric Tutor, Necropotence, Black Market Connections
- Red: Dockside Extortionist, Chaos Warp, Blasphemous Act, Jeska's Will, Deflecting Swat, Vandalblast
- Green: Cultivate, Beast Within, Heroic Intervention, Kodama's Reach, Nature's Lore, Three Visits, Sylvan Library

### Archetype Staple
Essential for specific strategies but not universally played.
Examples: Skullclamp (aristocrats/tokens), Aura Shards (enchantress with creatures), Craterhoof Behemoth (creature-heavy), Reanimate (reanimator), Isochron Scepter (spell-based combo)

### Niche
Only useful in specific commanders or unique builds.
Examples: Phyrexian Obliterator (mono-black devotion), Zada Hedron Grinder (Zada-specific cantrip builds), Brudiclad (token copy strategies)

## Common Search Intent Patterns

When a player searches, they usually want one of these:

1. **Role fulfillment**: "I need more ramp" or "I need card draw" → cards that fill a specific deck-building role
2. **Problem solving**: "How do I deal with enchantments" or "I need graveyard hate" → answers to specific threats
3. **Strategy building**: "Cards for aristocrats" or "landfall payoffs" → cards that fit an archetype
4. **Budget alternatives**: "Cheaper version of Mana Crypt" or "budget ramp" → similar effect at lower price
5. **Synergy finding**: "Cards that care about creatures dying" or "landfall triggers" → cards with specific triggers
6. **Threat assessment**: "Best board wipes in black" or "blue counterspells" → strongest options in a color
7. **Protection needs**: "How to protect my commander" or "survive board wipes" → defensive options
8. **Filling curve gaps**: "Good 2-drops in green" or "cheap creatures" → cards at specific mana costs
9. **Win conditions**: "How do I win with this deck" or "finishers" → cards that close games
10. **Color-specific needs**: "Black card draw" or "red removal" → role + color combination

### Critical Tagging Distinctions

SACRIFICE OUTLET vs DEATH TRIGGER:
- Sacrifice outlet = you can CHOOSE to sacrifice a creature as a COST (Viscera Seer: "Sacrifice a creature: Scry 1")
- Death trigger = something happens when things die, but you can't choose to sacrifice (Grave Pact: "Whenever a creature you control dies, each other player sacrifices a creature")
- The test: does the card say "Sacrifice a creature:" as an activated ability? If yes = sacrifice_outlet. If it says "Whenever a creature dies" = death_trigger

SPECIFIC CARDS THAT ARE NOT SACRIFICE OUTLETS:
- Grave Pact = death_trigger ONLY. It says "whenever a creature you control dies" — it does NOT let you sacrifice anything. You need a SEPARATE sacrifice outlet to trigger it.
- Dictate of Erebos = death_trigger ONLY. Same reasoning.
- Blood Artist = death_trigger ONLY. It triggers on death but doesn't sacrifice.
- The word "sacrifice" appearing in a card's EFFECT (forcing opponents to sacrifice) does not make it a sacrifice_outlet. A sacrifice_outlet lets YOU choose to sacrifice YOUR creatures as a cost.

BOARD WIPE RECOGNITION:
- Any card that can destroy/exile/bounce ALL or MOST creatures is removal_board_wipe
- Overload cards like Cyclonic Rift are removal_board_wipe (the overload mode hits everything)
- Cards that say "destroy all creatures" = removal_board_wipe (Fumigate, Wrath of God, Damnation)
- A card can be BOTH removal_single AND removal_board_wipe if it has modes (Cyclonic Rift: single target normally, board wipe when overloaded)

CLONE RECOGNITION:
- Cards that copy or become copies of other permanents should be tagged as "clone"
- Clever Impersonator, Clone, Phyrexian Metamorph, Sakashima = clone

GOAD AND POLITICS:
- Cards that force opponents to attack each other = goad
- Cards that create political dynamics or force opponents into bad choices = politics
- Kardur Doomscourge, Disrupt Decorum, Karazikar = goad

FINISHER RECOGNITION:
- Cards that can end the game or deal massive damage = finisher
- Gray Merchant of Asphodel draining 3 opponents for 10+ = finisher
- Avenger of Zendikar creating 15+ tokens = finisher + token_generator + etb_trigger (creates an army that grows with landfall — this wins games)
- If a card is how the deck WINS, it's a finisher

BLINK/FLICKER RECOGNITION:
- Cards that exile a permanent and return it = blink or flicker
- Conjurer's Closet, Thassa Deep-Dwelling, Brago, Restoration Angel = blink
- If a card's PRIMARY purpose is repeatedly triggering ETB effects through exile-and-return, tag it as "blink"
- Don't confuse with protection (Teferi's Protection phases out, that's protection not blink)

WHEEL RECOGNITION:
- Cards that make all players discard their hand and draw new cards = wheel
- Wheel of Fortune, Windfall, Wheel of Misfortune, Reforge the Soul = wheel
- Wheels are also card_draw but the "wheel" tag is important for wheel-specific strategies

EQUIPMENT THAT RAMPS:
- Equipment that untaps lands or produces mana when dealing combat damage = equipment + ramp
- Sword of Feast and Famine untaps ALL your lands = effectively doubles your mana = ramp
- Sword of the Animist searches for a land and puts it onto the battlefield = ramp
- Not all equipment is ramp — only ones that directly produce extra mana or lands

FINISHER MULTI-ROLE:
- Finishers often have secondary roles — tag ALL of them
- Gray Merchant of Asphodel = finisher + lifegain + etb_trigger (drains opponents, gains you life, triggers on entry)
- Craterhoof Behemoth = finisher + etb_trigger (buffs all creatures on entry)
- Torment of Hailfire = finisher + win_condition (X spell that can kill the table)

COUNTERSPELLS AND PROTECTION:
- Counterspells are "counterspell" role, NOT "protection" role
- Even though countering a spell protects your board, the primary function is countering, not protecting
- Force of Will, Counterspell, Swan Song = counterspell ONLY
- The exception: cards that directly grant hexproof/indestructible to your permanents = protection (Heroic Intervention, Lightning Greaves)

MONARCH RECOGNITION:
- Any card that says "you become the monarch" should include "monarch" as a role
- The monarch draws an extra card each turn, so monarch cards provide card_draw indirectly
- Court of Grace, Court of Bounty, Palace Jailer, Marchesa's Decree = monarch
- Always tag monarch cards with BOTH their primary role AND "monarch"

PROTECTION ROLE CLARITY:
- "Protection" role is ONLY for cards that protect OTHER things you control
- Heroic Intervention, Teferi's Protection, Lightning Greaves, Swiftfoot Boots = protection
- Cards with the KEYWORD "protection from [color/type]" on themselves = evasion NOT protection
- True-Name Nemesis = evasion ONLY. Its "protection from a player" only protects ITSELF
- Any creature with "protection from [color]" = evasion ONLY
- If a card only makes ITSELF hard to remove, that's evasion not protection
"""
The Ur-Dragon — 5-color Commander dragon tribal
100 cards total (including commander)
"""

DECK_NAME = "The Ur-Dragon EDH"
DECK_FORMAT = "commander"
DECK_DESCRIPTION = "5-color dragon tribal with ramp, removal, and card draw"

# (card_name, scryfall_id, quantity, board)
CARDS = [
    # === COMMANDER (1) ===
    ("The Ur-Dragon", "7e78b70b-0c67-4f14-8ad7-c9f8e3f59743", 1, "commander"),

    # === CREATURES — Dragons (25) ===
    ("Scion of the Ur-Dragon", "565b2a40-57b1-451f-8c1a-e1cf677d7f6b", 1, "main"),
    ("Tiamat", "6dd0b9b0-55f4-4ce7-a916-233571409e8c", 1, "main"),
    ("Old Gnawbone", "77ceba8b-de19-4db2-b5a7-f5df49bf4f37", 1, "main"),
    ("Goldspan Dragon", "9d914868-9000-4df2-a818-0ef8a7f636ae", 1, "main"),
    ("Lathliss, Dragon Queen", "54a4c37d-5eeb-42c9-9688-c2ed0d5044cd", 1, "main"),
    ("Dragonlord Atarka", "ce0c3b45-cf1d-4f51-8e36-be6e6f2abe5c", 1, "main"),
    ("Dragonlord Silumgar", "2eae504d-d4a9-440f-8ceb-df0571e5e8d2", 1, "main"),
    ("Dragonlord Ojutai", "a42b2c9c-1650-468e-94d6-e09b3d4af6aa", 1, "main"),
    ("Dragonlord Dromoka", "908042f3-0d03-4edf-816a-ec846a1e315f", 1, "main"),
    ("Dragonlord Kolaghan", "1cbf8933-32a1-44e7-984b-b6a6a8f1f5a9", 1, "main"),
    ("Utvara Hellkite", "33f6914d-808f-4502-a87a-571584e47e5d", 1, "main"),
    ("Scourge of the Throne", "5c594486-e4cf-4c32-8571-e5c554f7c5a8", 1, "main"),
    ("Terror of the Peaks", "432ecd5f-966f-4571-a422-8f7c4085cc0a", 1, "main"),
    ("Drakuseth, Maw of Flames", "d09e3c71-7f68-49d0-9e54-91e3530c6ee1", 1, "main"),
    ("Savage Ventmaw", "471cd229-c80f-4dc5-a174-96984fc80571", 1, "main"),
    ("Atarka, World Render", "e748dfb3-7250-450a-8895-741908b6016b", 1, "main"),
    ("Hellkite Charger", "4672fa00-9b08-4814-8066-f97ef46d26f9", 1, "main"),
    ("Balefire Dragon", "468d5308-2a6c-4f4b-b04b-824c1ab43278", 1, "main"),
    ("Bladewing the Risen", "27ce5f52-309c-4df4-b1c1-4ac3edfc80b4", 1, "main"),
    ("Thundermaw Hellkite", "a75f6bb4-ab06-42ca-a0df-326d9a098a26", 1, "main"),
    ("Niv-Mizzet, Parun", "6f3d2dc5-7b9d-4af6-9f3b-4de90fbf63c9", 1, "main"),
    ("Korvold, Fae-Cursed King", "92ea1575-eb64-43b5-b604-c6e23054f228", 1, "main"),
    ("Rith, Liberated Primeval", "a0e30e06-d4c4-4670-8baa-43e59a6a980b", 1, "main"),
    ("Miirym, Sentinel Wyrm", "a934590b-5571-4c07-aab7-1b3c1332a4e6", 1, "main"),
    ("Wrathful Red Dragon", "a29de940-4fa0-4058-85d4-3f2aeb1c10c0", 1, "main"),

    # === CREATURES — Support (5) ===
    ("Dragon's Herald", "263e3f8e-89d1-4d1f-a703-4cabe04858ca", 1, "main"),
    ("Dragonspeaker Shaman", "bfdedba0-fa73-4b78-8133-519f0b22de47", 1, "main"),
    ("Dragonborn Champion", "9fb72341-3a18-4e5d-8e61-29f070e7d22c", 1, "main"),
    ("Herald's Horn", "07b06421-778a-4d2b-abe6-3421c81a7564", 1, "main"),
    ("Urza's Incubator", "94e10f37-f06d-4204-8220-d3bbd2f3bc44", 1, "main"),

    # === RAMP / MANA (12) ===
    ("Sol Ring", "81e68861-c304-4b32-8576-d5ee71c6c45d", 1, "main"),
    ("Arcane Signet", "01b186af-8c7d-4f6c-a1e6-5f08e9f12eab", 1, "main"),
    ("Chromatic Lantern", "ea123356-3055-4e42-b816-ac3c4e9087d1", 1, "main"),
    ("Commander's Sphere", "bd4e5858-4e65-4a90-93a9-dab6e9e1e3f0", 1, "main"),
    ("Fellwar Stone", "1e60622b-7c25-444d-8eeb-c443acdfc488", 1, "main"),
    ("Dragon's Hoard", "5b441fc8-bc89-47d4-8745-2525aeb6c98c", 1, "main"),
    ("Cultivate", "b5c1c1c0-15e3-4efa-9c95-e815e3a5e010", 1, "main"),
    ("Kodama's Reach", "8d464c28-4bab-4aba-97b0-3a102e12def6", 1, "main"),
    ("Farseek", "061f0032-eb14-4c63-8231-aa61472b4b5c", 1, "main"),
    ("Nature's Lore", "a2a64307-b0ab-4f28-ad37-47d8b4c8b882", 1, "main"),
    ("Mirari's Wake", "329f8f3d-2fe6-44fa-802f-0c56e3f9998e", 1, "main"),
    ("Tempt with Discovery", "79248b68-4c2a-4428-8ad3-150ef5765891", 1, "main"),

    # === REMOVAL / INTERACTION (8) ===
    ("Swords to Plowshares", "80f46b80-0728-49bf-9d54-801eaa10b9b2", 1, "main"),
    ("Path to Exile", "2ee3e42e-120c-468a-b693-1067ec5e354e", 1, "main"),
    ("Cyclonic Rift", "ff08e5ed-f47b-4d8e-8b8b-41675ddbfc9f", 1, "main"),
    ("Anguished Unmaking", "90ced4fa-6509-4f7a-9da7-efc70de6f90c", 1, "main"),
    ("Beast Within", "ab3e096a-d6e8-4148-bbea-f26fc67e2fe2", 1, "main"),
    ("Crux of Fate", "11721b88-2654-482c-b928-4e3be032bf87", 1, "main"),
    ("Vanquisher's Banner", "60b7a85f-3a30-4ece-9bbb-61f3c4b796b8", 1, "main"),
    ("Kindred Dominance", "9794115a-5e70-4f47-99e8-0c26c5e100c7", 1, "main"),

    # === CARD DRAW / UTILITY (7) ===
    ("Temur Ascendancy", "11746bf1-d813-4ece-8b42-a0cee1f5af57", 1, "main"),
    ("Elemental Bond", "516ebdba-0f25-45a0-9c0c-51f31d03d7ee", 1, "main"),
    ("Garruk's Uprising", "71a4860a-8571-42ce-b72c-baa3461b615e", 1, "main"),
    ("Rishkar's Expertise", "5d58ba68-05c1-4cd8-a93d-321cd1739c00", 1, "main"),
    ("Return of the Wildspeaker", "b88a4943-bd1b-4d10-9cd3-b2ab91b25c10", 1, "main"),
    ("Sarkhan's Unsealing", "edcf421e-21c9-4e34-8b4f-d4507c19d8f9", 1, "main"),
    ("Rhythm of the Wild", "84062ce2-fea2-4e06-b83b-7cc597fb2a1b", 1, "main"),

    # === ENCHANTMENTS (2) ===
    ("Sylvan Library", "7a483778-b88b-473f-9217-7583e69b3c2f", 1, "main"),
    ("Smothering Tithe", "7af082fa-86a3-4f7b-966d-2be1f1d0c0bc", 1, "main"),

    # === ADDITIONAL CARDS — Filling to 100 (6) ===
    ("Fist of Suns", "2a4fe98d-5765-4662-bb79-4c27c9b10303", 1, "main"),
    ("Morophon, the Boundless", "9693e59b-032d-4ddc-a7d1-88a0f52dcc6c", 1, "main"),
    ("Wear // Tear", "d169a3b2-18ae-4414-98ef-d879676fdcc0", 1, "main"),
    ("Eladamri's Call", "42936b12-df0c-4332-a91f-2571a5ce7cc5", 1, "main"),
    ("Sarkhan, Fireblood", "b523c3e4-5464-4e46-aa14-7b3df8b46a4d", 1, "main"),
    ("Dragon Tempest", "f1933d08-07a7-45de-801f-073c476afeff", 1, "main"),

    # === LANDS (36) ===
    ("Command Tower", "6d28946a-a419-4613-8c93-7d5ebfc19bfb", 1, "main"),
    ("Exotic Orchard", "f9e3339b-3be7-4983-8e52-8571f3db38a3", 1, "main"),
    ("Path of Ancestry", "70e70720-d0b7-49c4-b515-4453089269f0", 1, "main"),
    ("Haven of the Spirit Dragon", "d4ba8429-5abd-4631-a4d7-d2d927932e2b", 1, "main"),
    ("Unclaimed Territory", "ff765732-6fe3-4571-a5ff-5c2a3b1b7eb4", 1, "main"),
    ("Stomping Ground", "dcaa1ff6-304e-4b28-a0de-cbc0456758b0", 1, "main"),
    ("Breeding Pool", "bb54233c-0844-4965-9cde-e8a4ef3e11b8", 1, "main"),
    ("Blood Crypt", "bd7cc9e0-5268-4acd-b6cb-0f78913d402e", 1, "main"),
    ("Temple Garden", "2b9b0195-beda-403e-bc27-7ae3be9f318c", 1, "main"),
    ("Hallowed Fountain", "f97a6564-e1b3-4811-a546-c345a1b1e43f", 1, "main"),
    ("Godless Shrine", "ced4c824-2dfc-42ae-84e6-09f8e3f51b5b", 1, "main"),
    ("Sacred Foundry", "b7b598d0-535d-477d-a33d-d6a10ff5439a", 1, "main"),
    ("Steam Vents", "b8ebe3cf-7143-453a-b0ef-2f5bdaac3185", 1, "main"),
    ("Overgrown Tomb", "eff1f52c-5c43-4f0e-87bf-f516d7b22c6c", 1, "main"),
    ("Watery Grave", "7d4595f2-9297-40dc-b2dd-7144bbb401f7", 1, "main"),
    ("Forest", "b6098e5c-4766-4a93-a562-1a71c0af1a24", 3, "main"),
    ("Mountain", "3a3e14e1-2e6f-4e99-8c14-660b6719cb78", 3, "main"),
    ("Plains", "8e0a4a82-0dbb-4348-9a56-0a9dfab1daa0", 2, "main"),
    ("Island", "9c0f3fbb-dc6e-4e0d-8f1f-4a2e4a0c79e5", 2, "main"),
    ("Swamp", "6c8c3f0e-d5e1-4e6a-a4be-24181c5a8c52", 2, "main"),
    ("Cinder Glade", "5a9db48e-9a04-4f78-9f99-5e7f34bfd72d", 1, "main"),
    ("Canopy Vista", "a3262c7f-4fdf-4648-9f04-0e0aa043db8f", 1, "main"),
    ("Prairie Stream", "b9bc9e0e-8725-46f1-b894-e7443e72241b", 1, "main"),
    ("Sunken Hollow", "0c0b6482-11c3-4b42-9509-46d7ef7c8e0f", 1, "main"),
    ("Smoldering Marsh", "359b189d-aa51-4e90-820a-e79884562e34", 1, "main"),
    ("Rogue's Passage", "766b7834-f54e-4439-94c0-0d4382851217", 1, "main"),
    ("Bojuka Bog", "0105a725-4911-47cb-b2c6-98541e3c6d67", 1, "main"),
]
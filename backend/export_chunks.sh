@"
#!/bin/bash
psql -U mtg_user -d mtg_deck_intelligence -c "COPY (SELECT * FROM cards ORDER BY name LIMIT 5000) TO '/tmp/cards_1.dat'"
psql -U mtg_user -d mtg_deck_intelligence -c "COPY (SELECT * FROM cards ORDER BY name OFFSET 5000 LIMIT 5000) TO '/tmp/cards_2.dat'"
psql -U mtg_user -d mtg_deck_intelligence -c "COPY (SELECT * FROM cards ORDER BY name OFFSET 10000 LIMIT 5000) TO '/tmp/cards_3.dat'"
psql -U mtg_user -d mtg_deck_intelligence -c "COPY (SELECT * FROM cards ORDER BY name OFFSET 15000 LIMIT 5000) TO '/tmp/cards_4.dat'"
psql -U mtg_user -d mtg_deck_intelligence -c "COPY (SELECT * FROM cards ORDER BY name OFFSET 20000 LIMIT 5000) TO '/tmp/cards_5.dat'"
psql -U mtg_user -d mtg_deck_intelligence -c "COPY (SELECT * FROM cards ORDER BY name OFFSET 25000 LIMIT 5000) TO '/tmp/cards_6.dat'"
psql -U mtg_user -d mtg_deck_intelligence -c "COPY (SELECT * FROM cards ORDER BY name OFFSET 30000 LIMIT 5000) TO '/tmp/cards_7.dat'"
ls -lh /tmp/cards_*.dat
"@ | Out-File -FilePath export_chunks.sh -Encoding ascii
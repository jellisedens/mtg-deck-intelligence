import csv
import json

tags = []
with open('tags_export.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        tag = {
            'name': row['name'],
            'roles': json.loads(row['roles']) if row['roles'] else [],
            'archetypes': json.loads(row['archetypes']) if row['archetypes'] else [],
            'search_terms': json.loads(row['search_terms']) if row['search_terms'] else [],
            'synergies': json.loads(row['synergies']) if row['synergies'] else [],
            'power_level': row['power_level'] or None,
            'summary': row['strategic_summary'] or None,
        }
        tags.append(tag)

with open('backend/scripts/seed_tags.json', 'w') as f:
    json.dump(tags, f)

print(f'Converted {len(tags)} tags')
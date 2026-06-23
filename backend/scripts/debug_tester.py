import sys
sys.path.insert(0, "/app")
from services.tag_index import is_index_loaded, get_index_size, get_card_tags

print(f"Index loaded: {is_index_loaded()}, size: {get_index_size()}")

# Test a known oracle_id (Sol Ring)
test_id = "9ea14c07-ab77-4faa-9912-77753e2313c3"
tags = get_card_tags(test_id)
print(f"Sol Ring tags: {tags}")

# Check if index has any data
if is_index_loaded():
    from services.tag_index import _index
    sample_keys = list(_index.keys())[:3]
    for key in sample_keys:
        print(f"Sample: {key} -> {_index[key][:3]}")
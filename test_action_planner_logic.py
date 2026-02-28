import re
import sys
from nlp2cmd.automation.vector_store import get_vector_store

store = get_vector_store()
search_query = "lisa"
query_lower = search_query.lower()

base_query = query_lower
for suffix in ["a", "ek", "kiem", "ka", "y", "iego"]:
    if query_lower.endswith(suffix) and len(query_lower) > 3:
        base_query = query_lower[:-len(suffix)]
        break

print(f"query_lower: {query_lower}, base_query: {base_query}")

best_pattern = None
all_patterns = store.list_patterns()
for p_name in all_patterns:
    p = store.get_pattern(p_name)
    if p:
        if base_query in p.tags or query_lower in p.tags or base_query == p.name or query_lower == p.name:
            best_pattern = p
            print(f"Matched EXACT TAG: {p.name}")
            break

if not best_pattern:
    results = store.search(search_query, n_results=3, min_confidence=0.0)
    if results:
        print(f"Fallback to semantic match: {results[0][0].name} ({results[0][1]})")


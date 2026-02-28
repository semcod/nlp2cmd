import sys
from nlp2cmd.automation.vector_store import get_vector_store, DrawingPattern

store = get_vector_store()
# It seems "lis" didn't match the new fox_pattern, let's see if we added it properly.
print("Total patterns:", store.count())

# Try searching exactly for "lis"
res = store.search("lis", n_results=1)
if res:
    print(f"Match: {res[0][0].name}, conf: {res[0][1]}")
    if res[0][0].name == "fox":
        print("Steps:", len(res[0][0].steps))
else:
    print("No matches")


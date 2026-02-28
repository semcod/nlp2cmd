import sys
from nlp2cmd.automation.vector_store import get_vector_store

try:
    store = get_vector_store()
    print("Patterns count:", store.count())
except Exception as e:
    print(f"Error: {e}")


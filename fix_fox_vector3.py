import sys
from nlp2cmd.automation.vector_store import get_vector_store

store = get_vector_store()
# The issue is min_confidence in `_search_vector_db_for_pattern` is 0.6 and we got 0.69, so it SHOULD have matched `fox`.
# Wait, why did the previous output say "15 steps"? The fox has 31 steps.
# Oh! The output I got is:
# 🎯 Plan wykonania (15 kroków):
# Źródło: vector_db | Pewność: 66% | Est. czas: 6.0s
# 5. draw_filled_circle
# 7. draw_line x 8
# This looks like the "spider" or "flower" pattern maybe? Or something else that had 66% match.
# Wait, what if the vector store query in ActionPlanner stripped "lis" out or used something else?


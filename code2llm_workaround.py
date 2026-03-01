"""
Temporary workaround for code2llm package.
The actual code2llm wheel contains code2flow module, so we redirect to it.
"""

import sys
from code2flow.cli import main

if __name__ == '__main__':
    sys.exit(main())

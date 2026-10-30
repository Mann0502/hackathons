import os
import sys

# Make `import config`, `import engine...` work when running pytest from any folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

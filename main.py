import sys
import os

# Add src to path to allow imports from src/ifc_splitter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ifc_splitter.presentation.cli import main

if __name__ == "__main__":
    main()

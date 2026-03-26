"""
Shim module for running the app directly via `python app.py`.
The actual implementation is in src/swgoh_helper/app.py.
For normal usage, prefer the CLI commands: `rote-platoon`, `kyrotech`, etc.
"""

from swgoh_helper.app import main

if __name__ == "__main__":
    main()

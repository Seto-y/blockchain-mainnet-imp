#!/usr/bin/env python3

import sys
import os

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Bitcoin Node Map Server")
    print("=" * 60)
    print("This will:")
    print("  1. Start HTTP server (default: http://localhost:8000)")
    print("  2. Open map in browser")
    print("\nNote: The map displays data from bitcoin_nodes.json")
    print("To update the data, run:")
    print("  python -m backend.update_json")
    print("  or")
    print("  python main.py --create-heatmap")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)
    
    try:
        from backend.serve import main as serve_main
        serve_main()
    except KeyboardInterrupt:
        print("\n\nStopping server...")
        sys.exit(0)


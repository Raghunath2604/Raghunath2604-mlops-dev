#!/usr/bin/env python3
"""
Legacy wrapper for MLOps.dev Production Edge Agent.
Redirects to the production edge device runner in edge_device.py.
"""

from edge_device import main

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MLOps.dev Python SDK — Live Client Verification Suite
Validates 16 real operational workflows against the live control plane and SQLite database:
Device querying, model uploading, canary deployment, KL-divergence drift tracking,
device configuration updates, rollbacks, and audit trail validation.
"""

import os
import sys

# Ensure SDK is in path
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    # Execute full verification suite
    import demo

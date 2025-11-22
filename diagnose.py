#!/usr/bin/env python3
"""
Diagnostic script to debug import issues with Google packages
Run this to see what's going on with your Python environment
"""

import sys
import os

print("=" * 70)
print("PYTHON ENVIRONMENT DIAGNOSTIC")
print("=" * 70)

print(f"\nPython executable: {sys.executable}")
print(f"Python version: {sys.version}")

print("\n--- Python Path ---")
for i, p in enumerate(sys.path, 1):
    print(f"{i}. {p}")

print("\n--- Site Packages ---")
import site
for sp in site.getsitepackages():
    print(f"  {sp}")

print("\n--- Trying to import google packages ---")
packages = [
    'google',
    'google.auth',
    'google.auth.oauthlib',
    'google.auth.oauthlib.flow',
    'google.auth.httplib2',
    'google.api',
    'googleapiclient',
]

for pkg in packages:
    try:
        mod = __import__(pkg, fromlist=[''])
        location = getattr(mod, '__file__', 'N/A')
        print(f"✓ {pkg:35} → {location}")
    except ImportError as e:
        print(f"✗ {pkg:35} → {e}")

print("\n--- Checking pip list ---")
os.system("pip list | grep -i google")

print("\n" + "=" * 70)
print("DIAGNOSIS COMPLETE")
print("=" * 70)
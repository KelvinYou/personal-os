#!/usr/bin/env python3
"""Print the user's local date for Makefile targets."""
from __future__ import annotations

import argparse
from lib.clock import now_kl

parser = argparse.ArgumentParser()
parser.add_argument("--month", action="store_true")
args = parser.parse_args()
print(now_kl().strftime("%Y-%m" if args.month else "%Y-%m-%d"))

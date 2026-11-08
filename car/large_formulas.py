# Experiment: satypy on large random CNF formulas (hundreds of variables).
#
# The same experiment as medium_formulas.py (satypy against MiniSat with a conflict budget, on random k-CNF formulas
# with round(ratio * variables) clauses) with larger sizes and a smaller number of formulas per setting. See
# medium_formulas.py for the columns and the options.
#
# Works with satypy installed or not: the repository's own code is used (networkx and python-sat must be
# installed).
#
# Usage (from the repository root or from car/):
#   python car/large_formulas.py
#   python car/large_formulas.py --variables 100 200 --ratios 4.27 --repeat 3 --reference-conflicts 5000000
#
# Results are printed and written to car/large_formulas_results.csv.

import os
import sys

CAR = os.path.dirname(os.path.abspath(__file__))
if CAR not in sys.path:
    sys.path.insert(0, CAR)

import medium_formulas  # noqa: E402


def main():
    medium_formulas.benchmark(
        {"variables": [100, 200, 400], "ratios": [3.0, 4.0, 4.27, 4.5], "repeat": 3, "conflicts": 2_000_000},
        os.path.join(medium_formulas.REPO, "car", "large_formulas_results.csv"))


if __name__ == "__main__":
    main()

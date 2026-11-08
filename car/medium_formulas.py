# Experiment: satypy on medium-size random CNF formulas (tens to hundreds of variables).
#
# Every formula is decided by satypy (algorithm.solve: simplification, 2-SAT, or the bipartite MIDS graph of maximum degree 3 decided by the
# colour-forced set, with branching) and by MiniSat (python-sat) as the reference, and the answers are compared. The
# formulas are random k-CNF formulas with `variables` variables and round(ratio * variables) clauses
# (utils.random_formula); the ratios around 4.27 are the hard region of random 3-SAT, where both outcomes appear.
# MiniSat runs with a conflict budget (--reference-conflicts); when it does not finish, the formula has no reference
# answer and satypy's answer is only checked for consistency (a SAT answer is always verified against the formula).
#
# For each formula it reports the stage that decided it, the MIDS graph (vertices, edges, maximum degree), the size of
# the colour-forced independent dominating set, the clause vertices in it (unsat) and the time of satypy and of MiniSat.
#
# Works with satypy installed or not: the repository's own code is used (networkx and python-sat must be
# installed). large_formulas.py runs the same experiment on larger sizes.
#
# Usage (from the repository root or from car/):
#   python car/medium_formulas.py
#   python car/medium_formulas.py --variables 30 50 75 --ratios 3.5 4.27 --width 3 --repeat 10 --seed 7
#
# Results are printed and written to car/medium_formulas_results.csv.

import argparse
import csv
import os
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from satypy import algorithm, utils  # noqa: E402

COLUMNS = ["name", "variables", "clauses", "ratio", "reference", "answer", "correct", "stage", "mids_vertices",
           "mids_edges", "mids_max_degree", "mids_unsatisfied", "mids_size", "satypy_seconds",
           "reference_seconds"]


def reference_solve(formula, conflicts):
    """MiniSat 2.2 through python-sat with a budget of `conflicts` conflicts: True, False, or None if it did not finish."""
    from pysat.solvers import Minisat22  # noqa: PLC0415  (only needed by the experiments)
    with Minisat22(bootstrap_with=formula) as solver:
        solver.conf_budget(conflicts)
        return solver.solve_limited()


def run(name, formula, ratio, conflicts):
    variables = {abs(lit) for clause in formula for lit in clause}
    started = time.time()
    expected = reference_solve(formula, conflicts)
    reference_seconds = time.time() - started
    stats = {}
    started = time.time()
    satisfiability, answer = algorithm.solve(formula, stats=stats)
    satypy_seconds = time.time() - started
    if satisfiability is True:
        correct = utils.satisfies(formula, answer) and expected is not False
    elif satisfiability is False:
        correct = None if expected is None else not expected
    else:
        correct = None
    row = {"name": name, "variables": len(variables), "clauses": len(formula), "ratio": f"{ratio:g}",
           "reference": {True: "SAT", False: "UNSAT", None: "unknown"}[expected],
           "answer": {True: "SAT", False: "UNSAT", None: "UNKNOWN"}[satisfiability],
           "correct": "unknown" if correct is None else ("yes" if correct else "NO"),
           "stage": stats.get("stage", ""), "satypy_seconds": f"{satypy_seconds:.3f}",
           "reference_seconds": f"{reference_seconds:.3f}"}
    for key in ("mids_vertices", "mids_edges", "mids_max_degree", "mids_unsatisfied", "mids_size"):
        if key in stats:
            row[key] = stats[key]
    return row


def benchmark(defaults, default_output):
    arguments = argparse.ArgumentParser(description="Check satypy against MiniSat on random formulas.")
    arguments.add_argument("--variables", nargs="+", type=int, default=defaults["variables"],
                           help=f"numbers of variables (default {' '.join(map(str, defaults['variables']))})")
    arguments.add_argument("--ratios", nargs="+", type=float, default=defaults["ratios"],
                           help=f"clauses / variables (default {' '.join(map(str, defaults['ratios']))})")
    arguments.add_argument("--width", type=int, default=3, help="literals per clause (default 3)")
    arguments.add_argument("--repeat", type=int, default=defaults["repeat"],
                           help=f"random formulas per setting (default {defaults['repeat']})")
    arguments.add_argument("--seed", type=int, default=2026, help="random seed (default 2026)")
    arguments.add_argument("--reference-conflicts", type=int, default=defaults["conflicts"],
                           help=f"conflict budget of MiniSat (default {defaults['conflicts']})")
    arguments.add_argument("-o", "--output", default=default_output)
    args = arguments.parse_args()

    rng = random.Random(args.seed)
    rows = []
    print(f"{'name':<34}{'V':>6}{'m':>7} {'ref':<8} {'answer':<8} {'correct':<8} {'stage':<26}{'n':>9}{'|S|':>8}"
          f"{'satypy s':>10}{'ref s':>8}")
    for num_variables in args.variables:
        for ratio in args.ratios:
            num_clauses = round(ratio * num_variables)
            for repetition in range(args.repeat):
                formula = utils.random_formula(num_variables, num_clauses, clause_size=args.width, rng=rng)
                name = f"random-v{num_variables}-r{ratio:g}-k{args.width}-{repetition}"
                row = run(name, formula, ratio, args.reference_conflicts)
                rows.append(row)
                print(f"{name:<34}{row['variables']:>6}{row['clauses']:>7} {row['reference']:<8} {row['answer']:<8} "
                      f"{row['correct']:<8} {row['stage']:<26}{row.get('mids_vertices', ''):>9}"
                      f"{row.get('mids_size', ''):>8}{row['satypy_seconds']:>10}{row['reference_seconds']:>8}",
                      flush=True)

    with open(args.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    def count(predicate):
        return sum(1 for row in rows if predicate(row))

    cut = [row for row in rows if str(row["stage"]).startswith("mids")]
    print()
    print(f"formulas: {len(rows)} (MiniSat: SAT {count(lambda r: r['reference'] == 'SAT')}, "
          f"UNSAT {count(lambda r: r['reference'] == 'UNSAT')}, no answer {count(lambda r: r['reference'] == 'unknown')})")
    print(f"satypy: SAT {count(lambda r: r['answer'] == 'SAT')}, UNSAT {count(lambda r: r['answer'] == 'UNSAT')}, "
          f"UNKNOWN {count(lambda r: r['answer'] == 'UNKNOWN')}")
    print(f"correct: {count(lambda r: r['correct'] == 'yes')}, wrong: {count(lambda r: r['correct'] == 'NO')}, "
          f"unchecked: {count(lambda r: r['correct'] == 'unknown')}")
    print(f"reached the MIDS graph: {len(cut)}; of those, MiniSat SAT {count(lambda r: r in cut and r['reference'] == 'SAT')}"
          f", answered SAT {count(lambda r: r in cut and r['answer'] == 'SAT')}")
    for row in rows:
        if row["correct"] == "NO":
            print(f"WRONG: {row['name']} reference {row['reference']}, answer {row['answer']}, stage {row['stage']}")
    print(f"results written to {args.output}")


def main():
    benchmark({"variables": [30, 50, 75], "ratios": [3.0, 4.0, 4.27, 4.5], "repeat": 5, "conflicts": 1_000_000},
              os.path.join(REPO, "car", "medium_formulas_results.csv"))


if __name__ == "__main__":
    main()

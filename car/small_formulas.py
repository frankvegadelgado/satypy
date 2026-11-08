# Experiment: correctness of satypy on very small CNF formulas.
#
# Every formula is decided by satypy (algorithm.solve: simplification, 2-SAT, or the bipartite MDS graph of maximum degree 3 decided by the
# colour-forced set, with branching) and by exhaustive search over all assignments, and the two answers are compared.
# The formulas are random k-CNF formulas with few variables (utils.random_formula) and the small DIMACS files of the
# repository (at most --max-file-variables variables).
#
# For the formulas that reach the MDS stage it also reports the graph (vertices, edges, maximum degree), the size of
# the colour-forced independent dominating set and the number of clause vertices in it (unsat).
#
# Works with satypy installed or not: the repository's own code is used (networkx must be installed).
#
# Usage (from the repository root or from car/):
#   python car/small_formulas.py
#   python car/small_formulas.py --variables 3 6 --clauses 16 --repeat 10 --seed 7
#   python car/small_formulas.py --no-files
#
# Results are printed and written to car/small_formulas_results.csv.

import argparse
import csv
import os
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from satypy import algorithm, parser, utils  # noqa: E402

DEFAULT_FILES = ["benchmarks/simple/file.cnf", "benchmarks/simple/tautology.cnf", "benchmarks/simple/trivial.cnf",
                 "benchmarks/test_formulas/formula0.cnf", "benchmarks/test_formulas/formula1.cnf",
                 "benchmarks/test_formulas/formula2.cnf", "benchmarks/test_formulas/formula3.cnf",
                 "benchmarks/test_formulas/planted_unique_v6_2.cnf"]
COLUMNS = ["name", "variables", "clauses", "expected", "answer", "correct", "stage", "mds_vertices",
           "mds_edges", "mds_max_degree", "mds_unsatisfied", "mds_size", "seconds"]


def run(name, formula):
    variables = {abs(lit) for clause in formula for lit in clause}
    expected, _ = utils.brute_force_solve(formula)
    stats = {}
    started = time.time()
    satisfiability, answer = algorithm.solve(formula, stats=stats)
    seconds = time.time() - started
    if satisfiability is True:
        correct = expected and utils.satisfies(formula, answer)
    elif satisfiability is False:
        correct = not expected
    else:
        correct = None
    row = {"name": name, "variables": len(variables), "clauses": len(formula),
           "expected": "SAT" if expected else "UNSAT",
           "answer": {True: "SAT", False: "UNSAT", None: "UNKNOWN"}[satisfiability],
           "correct": {True: "yes", False: "NO", None: "unknown"}[correct], "stage": stats.get("stage", ""),
           "seconds": f"{seconds:.3f}"}
    for key in ("mds_vertices", "mds_edges", "mds_max_degree", "mds_unsatisfied", "mds_size"):
        if key in stats:
            row[key] = stats[key]
    return row


def main():
    arguments = argparse.ArgumentParser(description="Check satypy against exhaustive search on very small formulas.")
    arguments.add_argument("--variables", nargs=2, type=int, default=[3, 5], metavar=("MIN", "MAX"),
                           help="range of the number of variables of the random formulas (default 3 5)")
    arguments.add_argument("--clauses", type=int, default=12, help="largest number of clauses (default 12)")
    arguments.add_argument("--width", type=int, default=3, help="literals per clause (default 3)")
    arguments.add_argument("--repeat", type=int, default=5, help="random formulas per (variables, clauses) (default 5)")
    arguments.add_argument("--seed", type=int, default=2026, help="random seed (default 2026)")
    arguments.add_argument("--max-file-variables", type=int, default=10,
                           help="largest number of variables of a DIMACS file to include (default 10)")
    arguments.add_argument("--no-files", action="store_true", help="only random formulas")
    arguments.add_argument("-o", "--output", default=os.path.join(REPO, "car", "small_formulas_results.csv"))
    args = arguments.parse_args()

    instances = []
    if not args.no_files:
        for relative in DEFAULT_FILES:
            path = os.path.join(REPO, relative)
            if not os.path.exists(path):
                continue
            formula = parser.read(path)
            if formula is None:
                continue
            formula = [list(clause) for clause in formula]
            if len({abs(lit) for clause in formula for lit in clause}) <= args.max_file_variables:
                instances.append((relative, formula))
    rng = random.Random(args.seed)
    for num_variables in range(args.variables[0], args.variables[1] + 1):
        for num_clauses in range(1, args.clauses + 1):
            for repetition in range(args.repeat):
                formula = utils.random_formula(num_variables, num_clauses, clause_size=args.width, rng=rng)
                instances.append((f"random-v{num_variables}-c{num_clauses}-r{repetition}", formula))

    rows = []
    print(f"{'name':<44}{'V':>3}{'m':>4} {'expected':<6} {'answer':<8} {'correct':<8} {'stage':<26}"
          f"{'n':>7}{'unsat':>7}{'|S|':>8}")
    for name, formula in instances:
        row = run(name, formula)
        rows.append(row)
        print(f"{name:<44}{row['variables']:>3}{row['clauses']:>4} {row['expected']:<6} {row['answer']:<8} "
              f"{row['correct']:<8} {row['stage']:<26}{row.get('mds_vertices', ''):>7}"
              f"{row.get('mds_unsatisfied', ''):>7}{row.get('mds_size', ''):>8}", flush=True)

    with open(args.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    def count(predicate):
        return sum(1 for row in rows if predicate(row))

    cut = [row for row in rows if str(row["stage"]).startswith("mds")]
    print()
    print(f"formulas: {len(rows)} (SAT {count(lambda r: r['expected'] == 'SAT')}, "
          f"UNSAT {count(lambda r: r['expected'] == 'UNSAT')})")
    print(f"correct: {count(lambda r: r['correct'] == 'yes')}, wrong: {count(lambda r: r['correct'] == 'NO')}, "
          f"unknown: {count(lambda r: r['correct'] == 'unknown')}")
    print(f"reached the MDS graph: {len(cut)} (correct {count(lambda r: r in cut and r['correct'] == 'yes')}, "
          f"wrong {count(lambda r: r in cut and r['correct'] == 'NO')}, "
          f"unknown {count(lambda r: r in cut and r['correct'] == 'unknown')})")
    for row in rows:
        if row["correct"] == "NO":
            print(f"WRONG: {row['name']} expected {row['expected']}, answer {row['answer']}, stage {row['stage']}")
    print(f"results written to {args.output}")


if __name__ == "__main__":
    main()

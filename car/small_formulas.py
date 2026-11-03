# Experiment: correctness of satypy on very small CNF formulas.
#
# Every formula is decided by satypy (algorithm.solve: simplification, 2-SAT, or the CNF -> MIDS graph solved
# with Siriaisa) and by exhaustive search over all assignments, and the two answers are compared. The formulas
# are random k-CNF formulas with few variables (utils.random_formula) and the small DIMACS files of the
# repository (at most --max-file-variables variables).
#
# For the formulas decided on the MIDS graph it also reports, with N variables and m clauses of the residual
# formula, bound copies per clause vertex and n vertices:
#   mids_size: size of Siriaisa's independent dominating set S (N when the residual formula is satisfiable and S
#     has no clause vertex; every independent dominating set with a clause vertex has at least bound + N);
#   ratio: |S| / N for satisfiable residual formulas, against 2 * sqrt(n);
#   lower_bound_ok: for unsatisfiable residual formulas, whether |S| >= bound + N;
#   splitting_excess: s(G) of the Siriaisa paper (k = floor(sqrt(n)), sum over vertices of degree > k of
#     ceil(deg / k) - 1), with i(G) + s(G) and 2 * N^2.
#
# Works with satypy installed or not: the repository's own code is used (siriaisa must be installed).
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
from math import isqrt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from satypy import algorithm, parser, reduction, utils  # noqa: E402

DEFAULT_FILES = ["benchmarks/simple/file.cnf", "benchmarks/simple/tautology.cnf", "benchmarks/simple/trivial.cnf",
                 "benchmarks/test_formulas/formula0.cnf", "benchmarks/test_formulas/formula1.cnf",
                 "benchmarks/test_formulas/formula2.cnf", "benchmarks/test_formulas/formula3.cnf"]
COLUMNS = ["name", "variables", "clauses", "expected", "answer", "correct", "stage", "residual_variables",
           "residual_clauses", "bound", "mids_vertices", "mids_edges", "mids_size", "ratio", "two_sqrt_n",
           "lower_bound_ok", "splitting_excess", "i_plus_s", "two_N_squared", "seconds"]


def splitting_excess(graph):
    """s(G) with k = max(1, floor(sqrt(n)))."""
    k = max(1, isqrt(graph.number_of_nodes()))
    return sum(-(-d // k) - 1 for _, d in graph.degree() if d > k)


def residual_mids_graph(formula):
    """The MIDS graph built by satypy for the residual formula, or None if the formula is decided earlier."""
    if not formula or any(len(clause) == 0 for clause in formula):
        return None
    max_variable = max(abs(lit) for clause in formula for lit in clause)
    clauses, _ = reduction.reduce_sat_to_simplified_sat(formula)
    if not clauses or all(len(clause) <= 2 for clause in clauses):
        return None
    graph, num_variables, bound = reduction.reduce_sat_to_mids(clauses, max_variable)
    return clauses, graph, num_variables, bound


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
    built = residual_mids_graph(formula) if str(stats.get("stage", "")).startswith("mids") else None
    if built is not None:
        clauses, graph, num_variables, bound = built
        residual_expected, _ = utils.brute_force_solve(clauses)
        n = graph.number_of_nodes()
        size = stats.get("mids_size")
        s = splitting_excess(graph)
        i_value = num_variables if residual_expected else None
        row.update(residual_variables=num_variables, residual_clauses=len(clauses), bound=bound, mids_vertices=n,
                   mids_edges=graph.number_of_edges(), mids_size=size, two_sqrt_n=f"{2 * n ** 0.5:.2f}",
                   splitting_excess=s, two_N_squared=2 * num_variables ** 2)
        if residual_expected:
            row.update(ratio=f"{size / num_variables:.4f}", i_plus_s=i_value + s)
        else:
            row.update(lower_bound_ok="yes" if size >= bound + num_variables else "NO")
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
    print(f"{'name':<44}{'V':>3}{'m':>4} {'expected':<6} {'answer':<8} {'correct':<8} {'stage':<20}"
          f"{'n':>8}{'|S|':>7}{'bound':>7}{'s(G)':>7}")
    for name, formula in instances:
        row = run(name, formula)
        rows.append(row)
        print(f"{name:<44}{row['variables']:>3}{row['clauses']:>4} {row['expected']:<6} {row['answer']:<8} "
              f"{row['correct']:<8} {row['stage']:<20}{row.get('mids_vertices', ''):>8}{row.get('mids_size', ''):>7}"
              f"{row.get('bound', ''):>7}{row.get('splitting_excess', ''):>7}", flush=True)

    with open(args.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    def count(predicate):
        return sum(1 for row in rows if predicate(row))

    mids = [row for row in rows if str(row["stage"]).startswith("mids")]
    print()
    print(f"formulas: {len(rows)} (SAT {count(lambda r: r['expected'] == 'SAT')}, "
          f"UNSAT {count(lambda r: r['expected'] == 'UNSAT')})")
    print(f"correct: {count(lambda r: r['correct'] == 'yes')}, wrong: {count(lambda r: r['correct'] == 'NO')}, "
          f"unknown: {count(lambda r: r['correct'] == 'unknown')}")
    print(f"decided on the MIDS graph: {len(mids)} (correct {count(lambda r: r in mids and r['correct'] == 'yes')}, "
          f"wrong {count(lambda r: r in mids and r['correct'] == 'NO')}, "
          f"unknown {count(lambda r: r in mids and r['correct'] == 'unknown')})")
    print(f"MIDS graph, unsatisfiable residual formula with |S| < bound + N: "
          f"{count(lambda r: r.get('lower_bound_ok') == 'NO')}")
    with_s = [row for row in mids if row.get("i_plus_s") not in (None, "")]
    if with_s:
        print(f"MIDS graph, satisfiable residual formula: {len(with_s)}; with i(G) + s(G) <= 2 N^2: "
              f"{sum(1 for row in with_s if row['i_plus_s'] <= row['two_N_squared'])}")
    for row in rows:
        if row["correct"] == "NO":
            print(f"WRONG: {row['name']} expected {row['expected']}, answer {row['answer']}, stage {row['stage']}")
    print(f"results written to {args.output}")


if __name__ == "__main__":
    main()

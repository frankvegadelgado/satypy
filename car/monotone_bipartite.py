# Experiment: CNF -> monotone 3SAT -> bipartite graph.
#
# For random k-CNF formulas (k = 2..--width, few variables) it reports:
#   - the reduction to monotone 3SAT (reduction.reduce_sat_to_monotone_3sat): every clause has at most 3 literals, all
#     positive or all negative (monotone_ok); the new variables (links, complements) against the k - 3 links per long
#     clause of the plain split (plain_links); equisatisfiability with the original formula (equisat), checked with
#     MiniSat on the monotone formula and by exhaustive search on the original one; and that a model of the monotone
#     formula restricted to the original variables satisfies the original formula (model_ok);
#   - the bipartite graph (reduction.reduce_monotone_3sat_to_bipartite): its number of vertices and edges and its
#     largest degree (3 at most).
#
# Works with satypy installed or not: the repository's own code is used. Needs networkx and python-sat (MiniSat).
#
# Usage (from the repository root or from car/):
#   python car/monotone_bipartite.py
#   python car/monotone_bipartite.py --variables 3 7 --clauses 14 --width 6 --repeat 5 --seed 7
#
# Results are printed and written to car/monotone_bipartite_results.csv.

import argparse
import csv
import os
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from satypy import reduction, utils  # noqa: E402

COLUMNS = ["name", "variables", "clauses", "width", "expected", "plain_links", "links", "complements",
           "new_variables", "monotone_variables", "monotone_clauses", "monotone_ok", "equisat", "model_ok",
           "bipartite_vertices", "bipartite_edges", "max_degree", "seconds"]


def is_monotone_3sat(clauses):
    return all(1 <= len(clause) <= 3 and (all(lit > 0 for lit in clause) or all(lit < 0 for lit in clause))
               for clause in clauses)


def run(name, formula, args):
    variables = {abs(lit) for clause in formula for lit in clause}
    max_variable = max(variables)
    expected, _ = utils.brute_force_solve(formula)
    started = time.time()
    monotone, info = reduction.reduce_sat_to_monotone_3sat(formula, max_variable)
    monotone_variables = {abs(lit) for clause in monotone for lit in clause}
    row = {"name": name, "variables": len(variables), "clauses": len(formula),
           "width": max(len(clause) for clause in formula), "expected": "SAT" if expected else "UNSAT",
           "plain_links": sum(max(0, len(clause) - 3) for clause in formula), "links": info["links"],
           "complements": len(info["complements"]), "new_variables": info["new_variables"],
           "monotone_variables": len(monotone_variables), "monotone_clauses": len(monotone),
           "monotone_ok": "yes" if is_monotone_3sat(monotone) else "NO"}

    satisfiable, model = utils.minisat_solve(monotone)
    row["equisat"] = "yes" if satisfiable == expected else "NO"
    if satisfiable:
        restricted = {lit for lit in model if abs(lit) <= max_variable}
        row["model_ok"] = "yes" if utils.satisfies(formula, restricted) else "NO"

    graph = reduction.reduce_monotone_3sat_to_bipartite(monotone)
    row.update(bipartite_vertices=graph.number_of_nodes(), bipartite_edges=graph.number_of_edges(),
               max_degree=max(degree for _, degree in graph.degree))
    row["seconds"] = f"{time.time() - started:.3f}"
    return row


def main():
    arguments = argparse.ArgumentParser(description="CNF -> monotone 3SAT -> bipartite graph.")
    arguments.add_argument("--variables", nargs=2, type=int, default=[3, 6], metavar=("MIN", "MAX"),
                           help="range of the number of variables of the random formulas (default 3 6)")
    arguments.add_argument("--clauses", type=int, default=10, help="largest number of clauses (default 10)")
    arguments.add_argument("--width", type=int, default=5, help="largest clause width, from 2 (default 5)")
    arguments.add_argument("--repeat", type=int, default=3, help="random formulas per setting (default 3)")
    arguments.add_argument("--seed", type=int, default=2026, help="random seed (default 2026)")
    arguments.add_argument("-o", "--output", default=os.path.join(REPO, "car", "monotone_bipartite_results.csv"))
    args = arguments.parse_args()

    rng = random.Random(args.seed)
    rows = []
    print(f"{'name':<28}{'V':>3}{'m':>4}{'k':>3} {'expected':<6} {'plain':>5}{'links':>6}{'compl':>6}{'mono':<5}"
          f"{'equisat':>8}{'maxdeg':>7}")
    for num_variables in range(args.variables[0], args.variables[1] + 1):
        for width in range(2, args.width + 1):
            for num_clauses in range(1, args.clauses + 1):
                for repetition in range(args.repeat):
                    formula = utils.random_formula(num_variables, num_clauses, clause_size=width, rng=rng)
                    name = f"random-v{num_variables}-k{width}-c{num_clauses}-r{repetition}"
                    row = run(name, formula, args)
                    rows.append(row)
                    print(f"{name:<28}{row['variables']:>3}{row['clauses']:>4}{row['width']:>3} {row['expected']:<6} "
                          f"{row['plain_links']:>5}{row['links']:>6}{row['complements']:>6} {row['monotone_ok']:<4}"
                          f"{row['equisat']:>8}{row.get('max_degree', ''):>7}", flush=True)

    with open(args.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    def count(predicate):
        return sum(1 for row in rows if predicate(row))

    sat = [row for row in rows if row["expected"] == "SAT"]
    print()
    print(f"formulas: {len(rows)} (SAT {len(sat)}, UNSAT {len(rows) - len(sat)})")
    print(f"monotone 3SAT: not monotone {count(lambda r: r['monotone_ok'] == 'NO')}, "
          f"not equisatisfiable {count(lambda r: r['equisat'] == 'NO')}, "
          f"model does not satisfy the original {count(lambda r: r.get('model_ok') == 'NO')}")
    print(f"new variables: {sum(r['new_variables'] for r in rows)} in total "
          f"(links {sum(r['links'] for r in rows)}, complements {sum(r['complements'] for r in rows)}), "
          f"plain split links {sum(r['plain_links'] for r in rows)}")
    print(f"bipartite graph: largest degree {max(r['max_degree'] for r in rows)}")
    print(f"results written to {args.output}")


if __name__ == "__main__":
    main()

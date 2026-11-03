# Experiment: the strategies of Siriaisa on the SAT-IDS graph of formulas built to stress the MIDS stage.
#
# satypy can be wrong only by answering UNSATISFIABLE on a satisfiable formula, which happens exactly when Siriaisa's
# set contains a clause vertex on the formula and on its branches (then |S| >= bound + N > 2N * N: ratio larger than 2N).
# Random formulas have many satisfying assignments; this script uses formulas that are harder for greedy choices:
#   planted-unique: random 3-CNF clauses satisfied by a planted assignment, added until it is the only solution;
#   nonconstant:    random satisfiable 3-CNF formulas satisfied by neither the all-True nor the all-False assignment;
#   unsat:          random unsatisfiable 3-CNF formulas.
# Only formulas whose residual formula (after unit propagation and pure literals) reaches the MIDS stage are kept.
#
# For each formula it reports satypy's answer against exhaustive search and the stage that decided it ("mids" when
# Siriaisa's set gives the assignment, "mids (branching)" when satypy split the formula on the clause named by
# Siriaisa's set, "mids (ratio rule)" for the ratio-2N rule) and, on the root SAT-IDS graph, the size of
# every strategy c1..c18 of Siriaisa (siriaisa.algorithm.final_candidates): for satisfiable residual formulas, which
# strategies return exactly N vertices (an optimal set, one literal per variable). It also checks Theorem
# "Independent domination and maximum satisfiability" of the Siriaisa paper on Siriaisa's output S (c18):
#   mu: least number of clauses of the residual formula falsified by an assignment (exhaustive search);
#   floor(|S| / bound) >= mu, and the literals of S, completed with False, falsify at most floor(|S| / bound) clauses.
#
# Works with satypy installed or not: the repository's own code is used (siriaisa must be installed).
#
# Usage (from the repository root or from car/):
#   python car/strategy_search.py
#   python car/strategy_search.py --variables 4 7 --count 10 --seed 11
#
# Results are printed and written to car/strategy_search_results.csv.

import argparse
import csv
import itertools
import os
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from siriaisa.algorithm import CANDIDATE_NAMES, final_candidates  # noqa: E402

from satypy import algorithm, reduction, utils  # noqa: E402

KINDS = ("planted-unique", "nonconstant", "unsat")
STRATEGIES = list(CANDIDATE_NAMES)
COLUMNS = (["name", "kind", "variables", "clauses", "solutions", "expected", "answer", "correct", "residual_variables",
            "stage", "residual_clauses", "bound", "mids_vertices", "mids_edges", "mids_size", "strategies_optimal", "mu",
            "floor_size_over_bound", "decoded_falsified", "maxsat_ok", "seconds"] + [f"size_{s}" for s in STRATEGIES])


def assignments(variables):
    for bits in itertools.product((False, True), repeat=len(variables)):
        yield {v if bit else -v for v, bit in zip(variables, bits, strict=True)}


def count_solutions(formula, variables):
    return sum(1 for literals in assignments(variables) if utils.satisfies(formula, literals))


def least_falsified(clauses):
    variables = sorted({abs(lit) for clause in clauses for lit in clause})
    return min(sum(1 for clause in clauses if not any(lit in literals for lit in clause))
               for literals in assignments(variables))


def random_clause(variables, rng, satisfied_by=None):
    while True:
        clause = [v if rng.random() < 0.5 else -v for v in rng.sample(variables, 3)]
        if satisfied_by is None or any(lit in satisfied_by for lit in clause):
            return clause


def planted_unique(num_variables, rng, max_clauses):
    variables = list(range(1, num_variables + 1))
    planted = {v if rng.random() < 0.5 else -v for v in variables}
    formula = []
    while len(formula) < max_clauses:
        formula.append(random_clause(variables, rng, planted))
        if len(formula) >= num_variables and count_solutions(formula, variables) == 1:
            return formula
    return None


def nonconstant(num_variables, num_clauses, rng):
    variables = list(range(1, num_variables + 1))
    formula = [random_clause(variables, rng) for _ in range(num_clauses)]
    if utils.satisfies(formula, set(variables)) or utils.satisfies(formula, {-v for v in variables}):
        return None
    return formula if count_solutions(formula, variables) > 0 else None


def unsatisfiable(num_variables, num_clauses, rng):
    variables = list(range(1, num_variables + 1))
    formula = [random_clause(variables, rng) for _ in range(num_clauses)]
    return formula if count_solutions(formula, variables) == 0 else None


def residual_graph(formula):
    """The SAT-IDS graph satypy builds for the residual formula, or None if an earlier stage decides it."""
    max_variable = max(abs(lit) for clause in formula for lit in clause)
    clauses, _ = reduction.reduce_sat_to_simplified_sat(formula)
    if not clauses or all(len(clause) <= 2 for clause in clauses):
        return None
    graph, num_variables, bound = reduction.reduce_sat_to_mids(clauses, max_variable)
    return clauses, max_variable, graph, num_variables, bound


def generate(kind, num_variables, rng, max_clauses, attempts):
    for _ in range(attempts):
        if kind == "planted-unique":
            formula = planted_unique(num_variables, rng, max_clauses)
        elif kind == "nonconstant":
            formula = nonconstant(num_variables, rng.randint(num_variables, max_clauses), rng)
        else:
            formula = unsatisfiable(num_variables, rng.randint(2 * num_variables, max_clauses), rng)
        if formula is not None and residual_graph(formula) is not None:
            return formula
    return None


def run(name, kind, formula):
    variables = sorted({abs(lit) for clause in formula for lit in clause})
    solutions = count_solutions(formula, variables)
    started = time.time()
    stats = {}
    satisfiability, answer = algorithm.solve(formula, stats=stats)
    if satisfiability is True:
        correct = solutions > 0 and utils.satisfies(formula, answer)
    elif satisfiability is False:
        correct = solutions == 0
    else:
        correct = None
    clauses, max_variable, graph, num_variables, bound = residual_graph(formula)
    candidates = final_candidates(graph)
    seconds = time.time() - started
    output = candidates["c18"]
    size = len(output)
    mu = least_falsified(clauses)
    residual_satisfiable = mu == 0
    literals = reduction.decode_mids(output, max_variable)
    residual_variables = {abs(lit) for clause in clauses for lit in clause}
    completed = literals | {-v for v in residual_variables if v not in literals and -v not in literals}
    falsified = sum(1 for clause in clauses if not any(lit in completed for lit in clause))
    floor_ratio = size // bound
    row = {"name": name, "kind": kind, "variables": len(variables), "clauses": len(formula), "solutions": solutions,
           "expected": "SAT" if solutions else "UNSAT",
           "answer": {True: "SAT", False: "UNSAT", None: "UNKNOWN"}[satisfiability],
           "correct": {True: "yes", False: "NO", None: "unknown"}[correct], "stage": stats.get("stage", ""),
           "residual_variables": num_variables, "residual_clauses": len(clauses), "bound": bound,
           "mids_vertices": graph.number_of_nodes(), "mids_edges": graph.number_of_edges(), "mids_size": size,
           "strategies_optimal": " ".join(s for s in STRATEGIES if len(candidates[s]) == num_variables)
           if residual_satisfiable else "",
           "mu": mu, "floor_size_over_bound": floor_ratio, "decoded_falsified": falsified,
           "maxsat_ok": "yes" if floor_ratio >= mu and falsified <= floor_ratio else "NO", "seconds": f"{seconds:.3f}"}
    row.update({f"size_{s}": len(candidates[s]) for s in STRATEGIES})
    return row


def main():
    arguments = argparse.ArgumentParser(description="Siriaisa's strategies on SAT-IDS graphs of stress formulas.")
    arguments.add_argument("--variables", nargs=2, type=int, default=[3, 6], metavar=("MIN", "MAX"),
                           help="range of the number of variables (default 3 6)")
    arguments.add_argument("--count", type=int, default=5, help="formulas per kind and number of variables (default 5)")
    arguments.add_argument("--max-clauses", type=int, default=16, help="largest number of clauses (default 16)")
    arguments.add_argument("--attempts", type=int, default=2000, help="generation attempts per formula (default 2000)")
    arguments.add_argument("--seed", type=int, default=2026, help="random seed (default 2026)")
    arguments.add_argument("-o", "--output", default=os.path.join(REPO, "car", "strategy_search_results.csv"))
    args = arguments.parse_args()

    rng = random.Random(args.seed)
    rows = []
    print(f"{'name':<28}{'kind':<16}{'V':>3}{'m':>4}{'sol':>5} {'answer':<8}{'correct':<8}{'stage':<19}{'n':>8}"
          f"{'|S|':>6}{'mu':>4}  optimal strategies")
    for num_variables in range(args.variables[0], args.variables[1] + 1):
        for kind in KINDS:
            for index in range(args.count):
                formula = generate(kind, num_variables, rng, args.max_clauses, args.attempts)
                name = f"{kind}-v{num_variables}-{index}"
                if formula is None:
                    print(f"{name:<28}not generated (no formula reached the MIDS stage)")
                    continue
                row = run(name, kind, formula)
                rows.append(row)
                print(f"{name:<28}{kind:<16}{row['variables']:>3}{row['clauses']:>4}{row['solutions']:>5} "
                      f"{row['answer']:<8}{row['correct']:<8}{row['stage']:<19}{row['mids_vertices']:>8}{row['mids_size']:>6}"
                      f"{row['mu']:>4}  {row['strategies_optimal']}", flush=True)

    with open(args.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"formulas: {len(rows)}; correct: {sum(r['correct'] == 'yes' for r in rows)}, "
          f"wrong: {sum(r['correct'] == 'NO' for r in rows)}, unknown: {sum(r['correct'] == 'unknown' for r in rows)}")
    for stage in sorted({r["stage"] for r in rows}):
        print(f"  decided by {stage}: {sum(r['stage'] == stage for r in rows)}")
    satisfiable = [r for r in rows if r["mu"] == 0]
    print(f"satisfiable residual formulas: {len(satisfiable)}; Siriaisa's output on the root graph optimal (|S| = N): "
          f"{sum(r['mids_size'] == r['residual_variables'] for r in satisfiable)}")
    for strategy in STRATEGIES:
        hits = sum(strategy in r["strategies_optimal"].split() for r in satisfiable)
        print(f"  {strategy:<4} optimal on {hits:>4} of {len(satisfiable)}  ({CANDIDATE_NAMES[strategy]})")
    print(f"maximum satisfiability check (floor(|S|/bound) >= mu, decoded assignment within it): "
          f"{sum(r['maxsat_ok'] == 'yes' for r in rows)} of {len(rows)}")
    for row in rows:
        if row["correct"] == "NO":
            print(f"WRONG: {row['name']} expected {row['expected']}, answer {row['answer']}")
    print(f"results written to {args.output}")


if __name__ == "__main__":
    main()

# Experiment: search for a counterexample of satypy on small and medium satisfiable CNF formulas.
#
# A counterexample is a satisfiable formula that satypy answers UNSATISFIABLE (the only wrong answer it can give: a
# SATISFIABLE answer is always verified against the formula). Such an answer comes from a leaf of the branching, where
# UNSATISFIABLE rests on the assumption that the MIDS search finds an independent dominating set without clause vertices
# whenever one exists. Every formula generated here is satisfiable by construction (a planted solution) or is checked
# satisfiable by MiniSat, so the reference answer is always SAT.
#
# The formulas are chosen to be hard for a local search, i.e. to have few solutions or a rigid structure:
#   planted   random 3-CNF formulas with a planted solution at ratios 4.0, 4.27, 4.5
#   unique    formulas with exactly one solution (clauses are added until MiniSat finds no second solution)
#   mixed     random formulas with clauses of 2, 3 and 4 literals and a planted solution
#   xor       systems of 3-variable parity equations (4 clauses each) with a planted solution
#   coloring  3-colouring of random graphs of average degree 4.2, 4.5, 4.7 with a planted colouring (2 and 3 literals)
#   random    uniform random 3-CNF formulas at ratios 4.0, 4.27, 4.5, kept only if MiniSat finds them satisfiable
# Each formula is also given in --variants relabelled forms (variables permuted, then renumbered with gaps; clauses and
# literals shuffled): the search depends on the order of the graph, so each form is a new trial on the same formula.
#
# For every formula it reports the stage that decided it and the time of satypy. It counts separately the satisfiable
# formulas on which the first search failed and the branching or the decoding found the assignment (stage
# "mids (branching)" or "mids (decoded)"). Every counterexample is written as a DIMACS file to car/counterexamples/.
#
# Works with satypy installed or not: the repository's own code is used (networkx and python-sat must be installed).
#
# Usage (from the repository root or from car/):
#   python car/counterexample_search.py
#   python car/counterexample_search.py --sizes 20 30 40 --repeat 10 --variants 5 --minutes 60 --seed 7
#   python car/counterexample_search.py --families unique xor coloring --stop-after 1
#
# Results are printed and written to car/counterexample_search_results.csv.

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

from satypy import algorithm, utils  # noqa: E402

FAMILIES = ["planted", "unique", "mixed", "xor", "coloring", "random"]
SETTINGS = {"planted": [4.0, 4.27, 4.5], "unique": [3.0], "mixed": [3.0, 3.5, 4.0], "xor": [0.8, 1.0, 1.2],
            "coloring": [4.2, 4.5, 4.7], "random": [4.0, 4.27, 4.5]}
COLUMNS = ["name", "family", "setting", "variant", "variables", "clauses", "reference", "answer", "correct", "stage",
           "mids_vertices", "mids_edges", "mids_max_degree", "mids_unsatisfied", "satypy_seconds"]
RESCUED = ("mids (branching)", "mids (decoded)")


def holds(clause, solution):
    return any((lit > 0) == solution[abs(lit)] for lit in clause)


def planted_clauses(n, count, rng, solution, widths=((3, 1.0),)):
    """`count` random clauses over 1..n, each satisfied by `solution`."""
    clauses = []
    sizes = [size for size, _ in widths]
    weights = [weight for _, weight in widths]
    while len(clauses) < count:
        size = min(rng.choices(sizes, weights)[0], n)
        clause = [v if rng.random() < 0.5 else -v for v in rng.sample(range(1, n + 1), size)]
        if holds(clause, solution):
            clauses.append(clause)
    return clauses


def planted_formula(n, ratio, rng):
    solution = {v: rng.random() < 0.5 for v in range(1, n + 1)}
    return planted_clauses(n, round(ratio * n), rng, solution), solution


def mixed_formula(n, ratio, rng):
    solution = {v: rng.random() < 0.5 for v in range(1, n + 1)}
    return planted_clauses(n, round(ratio * n), rng, solution, widths=((2, 0.1), (3, 0.7), (4, 0.2))), solution


def unique_formula(n, ratio, rng):
    """Planted formula with exactly one solution: while MiniSat finds a second solution, add a clause that this solution
    violates and the planted one satisfies."""
    from pysat.solvers import Minisat22  # noqa: PLC0415  (only needed by the experiments)
    n = max(n, 4)
    solution = {v: rng.random() < 0.5 for v in range(1, n + 1)}
    clauses = planted_clauses(n, round(ratio * n), rng, solution)
    blocking = [-v if solution[v] else v for v in range(1, n + 1)]
    with Minisat22(bootstrap_with=clauses + [blocking]) as solver:
        for _ in range(20000):
            if not solver.solve():
                return clauses, solution
            value = {abs(lit): lit > 0 for lit in solver.get_model() if abs(lit) <= n}
            first = rng.choice([v for v in range(1, n + 1) if value[v] != solution[v]])
            others = rng.sample([v for v in range(1, n + 1) if v != first], 2)
            clause = [-v if value[v] else v for v in [first] + others]
            rng.shuffle(clause)
            clauses.append(clause)
            solver.add_clause(clause)
    return None


def xor_formula(n, ratio, rng):
    solution = {v: rng.random() < 0.5 for v in range(1, n + 1)}
    clauses = []
    for _ in range(max(1, round(ratio * n))):
        variables = rng.sample(range(1, n + 1), 3)
        parity = sum(solution[v] for v in variables) % 2
        for bits in itertools.product((False, True), repeat=3):
            if sum(bits) % 2 != parity:
                clauses.append([-v if bit else v for v, bit in zip(variables, bits, strict=True)])
    return clauses, solution


def coloring_formula(n, degree, rng):
    vertices = max(9, n // 3)
    classes = [i % 3 for i in range(vertices)]
    rng.shuffle(classes)
    edges = set()
    available = sum(classes[i] != classes[j] for i, j in itertools.combinations(range(vertices), 2))
    target = min(round(degree * vertices / 2), available)
    while len(edges) < target:
        i, j = sorted(rng.sample(range(vertices), 2))
        if classes[i] != classes[j]:
            edges.add((i, j))

    def var(i, color):
        return 3 * i + color + 1

    clauses = []
    for i in range(vertices):
        clauses.append([var(i, 0), var(i, 1), var(i, 2)])
        clauses.extend([-var(i, a), -var(i, b)] for a, b in itertools.combinations(range(3), 2))
    for i, j in sorted(edges):
        clauses.extend([-var(i, color), -var(j, color)] for color in range(3))
    solution = {var(i, color): classes[i] == color for i in range(vertices) for color in range(3)}
    return clauses, solution


def random_satisfiable_formula(n, ratio, rng, conflicts):
    from pysat.solvers import Minisat22  # noqa: PLC0415  (only needed by the experiments)
    formula = utils.random_formula(n, round(ratio * n), clause_size=3, rng=rng)
    with Minisat22(bootstrap_with=formula) as solver:
        solver.conf_budget(conflicts)
        return (formula, None) if solver.solve_limited() is True else None


def make(family, size, setting, rng, conflicts):
    """(formula, planted solution or None), or None if no satisfiable formula was produced."""
    if family == "planted":
        return planted_formula(size, setting, rng)
    if family == "unique":
        return unique_formula(size, setting, rng)
    if family == "mixed":
        return mixed_formula(size, setting, rng)
    if family == "xor":
        return xor_formula(size, setting, rng)
    if family == "coloring":
        return coloring_formula(size, setting, rng)
    return random_satisfiable_formula(size, setting, rng, conflicts)


def relabel(formula, rng, gaps):
    """The same formula with its variables permuted (renumbered with gaps if `gaps`), and its clauses and literals shuffled."""
    variables = sorted({abs(lit) for clause in formula for lit in clause})
    top = 10 * len(variables) if gaps else len(variables)
    ids = rng.sample(range(1, top + 1), len(variables))
    new = dict(zip(variables, ids, strict=True))
    result = [[new[abs(lit)] if lit > 0 else -new[abs(lit)] for lit in clause] for clause in formula]
    for clause in result:
        rng.shuffle(clause)
    rng.shuffle(result)
    return result


def write_dimacs(path, formula, comments):
    top = max(abs(lit) for clause in formula for lit in clause)
    with open(path, "w") as handle:
        for comment in comments:
            handle.write(f"c {comment}\n")
        handle.write(f"p cnf {top} {len(formula)}\n")
        for clause in formula:
            handle.write(" ".join(map(str, clause)) + " 0\n")


def run(name, family, setting, variant, formula):
    stats = {}
    started = time.time()
    satisfiability, answer = algorithm.solve(formula, stats=stats)
    seconds = time.time() - started
    if satisfiability is True:
        correct = "yes" if utils.satisfies(formula, answer) else "NO"
    elif satisfiability is False:
        correct = "NO"
    else:
        correct = "unknown"
    row = {"name": name, "family": family, "setting": f"{setting:g}", "variant": variant,
           "variables": len({abs(lit) for clause in formula for lit in clause}), "clauses": len(formula),
           "reference": "SAT", "answer": {True: "SAT", False: "UNSAT", None: "UNKNOWN"}[satisfiability],
           "correct": correct, "stage": stats.get("stage", ""), "satypy_seconds": f"{seconds:.3f}"}
    for key in ("mids_vertices", "mids_edges", "mids_max_degree", "mids_unsatisfied"):
        if key in stats:
            row[key] = stats[key]
    return row


def main():
    arguments = argparse.ArgumentParser(description="Search for a satisfiable formula that satypy answers UNSATISFIABLE.")
    arguments.add_argument("--families", nargs="+", choices=FAMILIES, default=FAMILIES)
    arguments.add_argument("--sizes", nargs="+", type=int, default=[20, 30, 40, 50, 60],
                           help="approximate numbers of variables (default 20 30 40 50 60)")
    arguments.add_argument("--repeat", type=int, default=6, help="formulas per family and size (default 6)")
    arguments.add_argument("--variants", type=int, default=3,
                           help="forms of each formula: the original and relabelled ones (default 3)")
    arguments.add_argument("--seed", type=int, default=2026, help="random seed (default 2026)")
    arguments.add_argument("--minutes", type=float, default=30, help="time budget of the whole search (default 30)")
    arguments.add_argument("--stop-after", type=int, default=3, help="stop after this many counterexamples (default 3)")
    arguments.add_argument("--reference-conflicts", type=int, default=1_000_000,
                           help="conflict budget of MiniSat for the family random (default 1000000)")
    arguments.add_argument("-o", "--output", default=os.path.join(REPO, "car", "counterexample_search_results.csv"))
    arguments.add_argument("--counterexamples", default=os.path.join(REPO, "car", "counterexamples"),
                           help="folder of the DIMACS files of the counterexamples")
    args = arguments.parse_args()

    rng = random.Random(args.seed)
    deadline = time.time() + 60 * args.minutes
    rows = []
    found = []
    stopped = False
    print(f"{'name':<34}{'V':>5}{'m':>6} {'answer':<8} {'correct':<8} {'stage':<20}{'satypy s':>10}")
    for size in args.sizes:
        for repetition in range(args.repeat):
            for family in args.families:
                if stopped:
                    break
                setting = SETTINGS[family][repetition % len(SETTINGS[family])]
                made = make(family, size, setting, rng, args.reference_conflicts)
                if made is None:
                    continue
                base, solution = made
                if solution is not None and not all(holds(clause, solution) for clause in base):
                    print(f"generator error: {family} {size} {setting}", flush=True)
                    continue
                for variant in range(args.variants):
                    if time.time() > deadline:
                        stopped = True
                        print("time budget reached")
                        break
                    formula = base if variant == 0 else relabel(base, rng, gaps=variant % 2 == 0)
                    name = f"{family}-n{size}-s{setting:g}-{repetition}-v{variant}"
                    row = run(name, family, setting, variant, formula)
                    rows.append(row)
                    print(f"{name:<34}{row['variables']:>5}{row['clauses']:>6} {row['answer']:<8} {row['correct']:<8} "
                          f"{row['stage']:<20}{row['satypy_seconds']:>10}", flush=True)
                    if row["correct"] == "NO":
                        os.makedirs(args.counterexamples, exist_ok=True)
                        path = os.path.join(args.counterexamples, name + ".cnf")
                        write_dimacs(path, formula, [f"counterexample of satypy: satisfiable, answered {row['answer']}",
                                                     f"family {family}, setting {setting:g}, variant {variant}, "
                                                     f"seed {args.seed}"])
                        found.append(path)
                        print(f"COUNTEREXAMPLE written to {path}", flush=True)
                        if len(found) >= args.stop_after:
                            stopped = True
                            break
            if stopped:
                break
        if stopped:
            break

    with open(args.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"{'family':<10}{'formulas':>9}{'SAT':>6}{'UNSAT':>7}{'UNKNOWN':>9}{'rescued':>9}{'max s':>9}")
    for family in args.families:
        mine = [row for row in rows if row["family"] == family]
        if not mine:
            continue
        print(f"{family:<10}{len(mine):>9}{sum(r['answer'] == 'SAT' for r in mine):>6}"
              f"{sum(r['answer'] == 'UNSAT' for r in mine):>7}{sum(r['answer'] == 'UNKNOWN' for r in mine):>9}"
              f"{sum(r['answer'] == 'SAT' and r['stage'] in RESCUED for r in mine):>9}"
              f"{max(float(r['satypy_seconds']) for r in mine):>9.3f}")
    print(f"satisfiable formulas run: {len(rows)}; answered UNSAT (counterexamples): {len(found)}; "
          f"rescued = SAT answers found by the branching or the decoding after the first search failed")
    for path in found:
        print(f"COUNTEREXAMPLE: {path}")
    print(f"results written to {args.output}")


if __name__ == "__main__":
    main()

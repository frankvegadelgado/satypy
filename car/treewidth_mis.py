# Experiment: treewidth and maximum weight independent set of the 1-in-3 3SAT graph.
#
# For each DIMACS file: simplification (unit propagation and pure literals), then, if the residual
# formula is not 2-SAT, preprocessing (failed-literal probing, bounded variable elimination), then
# CNF -> 1-in-3 3SAT (clauses ordered by reverse Cuthill-McKee) -> MIS graph (triangle per clause,
# occurrence edges, a hub pair per variable (or, with -g cycle, the long even cycles); literal vertices
# weigh 2, partner and hub vertices 1). It reports:
#   primal_width / residual_primal_width: width of the primal graph of the formula / of the
#     preprocessed formula (a floor for the MIS graph's width, up to the heuristic);
#   graph_width: width of the MIS graph; reduced_vertices / reduced_width: after the MWIS reduction rules;
#   branches / dp_width: branchings and largest width solved by dynamic programming;
#   the maximum weight against the target (4m + hub pairs, or 4m with cycles), the decision and the running times,
# and compares the decision with MiniSat 2.2 (python-sat) and the yes/no in the file name.
# All widths are the smaller of networkx's minimum-degree and minimum-fill-in heuristics (upper bounds
# on the treewidth).
#
# Works with satypy installed or not: the repository's own code is used.
#
# Usage (from the repository root or from car/):
#   python car/treewidth_mis.py
#   python car/treewidth_mis.py -i benchmarks/simple benchmarks/file-dimacs-aim -t 120 -w 15
#   python car/treewidth_mis.py -g cycle
#
# Results are printed and written to car/treewidth_mis_results.csv.

import argparse
import csv
import multiprocessing as mp
import os
import queue
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import networkx as nx  # noqa: E402

from satypy import algorithm, parser, reduction  # noqa: E402

DEFAULT_DIRECTORIES = ["benchmarks/simple", "benchmarks/test_formulas", "benchmarks/file-dimacs-aim"]
COLUMNS = ["file", "variables", "clauses", "expected", "minisat", "primal_width", "stage", "residual_clauses",
           "eliminated", "residual_primal_width", "one_in_three_clauses", "vertices", "edges", "graph_width",
           "reduced_vertices", "reduced_width", "branches", "dp_width", "weight", "target", "decision", "agrees",
           "preprocess_seconds", "width_seconds", "mis_seconds", "status"]


def minisat(formula):
    try:
        from pysat.solvers import Minisat22
    except ImportError:
        return "n/a"
    if any(len(clause) == 0 for clause in formula):
        return "UNSAT"
    with Minisat22(bootstrap_with=formula) as solver:
        return "SAT" if solver.solve() else "UNSAT"


def primal_width(clauses):
    """Width of the best tree decomposition (upper bound on the treewidth) of the primal graph:
    variables, joined when they share a clause."""
    G = nx.Graph()
    for clause in clauses:
        variables = sorted({abs(literal) for literal in clause})
        G.add_nodes_from(variables)
        for j in range(len(variables)):
            for k in range(j + 1, len(variables)):
                G.add_edge(variables[j], variables[k])
    width = 0
    for nodes in nx.connected_components(G):
        if len(nodes) > 1:
            width = max(width, reduction.best_tree_decomposition(G.subgraph(nodes))[0])
    return width


def two_sat(formula, base, clauses, stack, variables):
    sat2, assignment = algorithm._solve_two_sat(clauses)
    if not sat2:
        return "UNSAT"
    return "SAT" if certify(formula, base, assignment, stack, variables) else "UNKNOWN"


def certify(formula, base, literals, stack, variables):
    assignment = set(base) | set(literals)
    assigned = {abs(lit) for lit in assignment}
    assignment |= {-v for v in variables if v not in assigned}
    ok, _ = algorithm.check(formula, reduction.extend_assignment(assignment, stack), set())
    return ok


def worker(path, out, max_width, gadget):
    formula = parser.read(path)
    variables = {abs(lit) for clause in formula for lit in clause}
    expected = getattr(formula, "expected_satisfiable", None)
    out.put({"variables": len(variables), "clauses": len(formula),
             "expected": "" if expected is None else ("SAT" if expected else "UNSAT")})
    out.put({"minisat": minisat(formula)})

    if not formula:
        out.put({"stage": "empty", "decision": "SAT", "status": "done"})
        return
    if any(len(clause) == 0 for clause in formula):
        out.put({"stage": "empty clause", "decision": "UNSAT", "status": "done"})
        return
    out.put({"primal_width": primal_width(formula)})
    max_variable = max(variables)
    clauses, solution = reduction.reduce_sat_to_simplified_sat(formula)
    if clauses is None:
        out.put({"stage": "simplification", "decision": "UNSAT", "status": "done"})
        return
    if not clauses:
        ok, _ = algorithm.check(formula, solution, set())
        out.put({"stage": "simplification", "decision": "SAT" if ok else "UNKNOWN", "status": "done"})
        return
    if all(len(clause) <= 2 for clause in clauses):
        out.put({"stage": "2-SAT", "decision": two_sat(formula, solution, clauses, [], variables), "status": "done"})
        return

    started = time.time()
    residual, committed, stack = reduction.preprocess(clauses)
    if residual is None:
        out.put({"stage": "preprocessing", "decision": "UNSAT", "status": "done"})
        return
    base = set(solution) | committed
    out.put({"residual_clauses": len(residual), "eliminated": len(stack),
             "preprocess_seconds": round(time.time() - started, 3)})
    if not residual:
        decision = "SAT" if certify(formula, base, set(), stack, variables) else "UNKNOWN"
        out.put({"stage": "preprocessing", "decision": decision, "status": "done"})
        return
    if all(len(clause) <= 2 for clause in residual):
        out.put({"stage": "2-SAT", "decision": two_sat(formula, base, residual, stack, variables), "status": "done"})
        return
    out.put({"residual_primal_width": primal_width(residual)})

    one_in_three = reduction.order_clauses(reduction.reduce_sat_to_one_in_three_sat(residual, max_variable))
    graph, target = reduction.reduce_one_in_three_sat_to_mis(one_in_three, gadget=gadget)
    out.put({"stage": "mis", "one_in_three_clauses": len(one_in_three), "vertices": graph.number_of_nodes(),
             "edges": graph.number_of_edges(), "target": target})

    started = time.time()
    width = 0
    for nodes in nx.connected_components(graph):
        if len(nodes) > 1:
            width = max(width, reduction.best_tree_decomposition(graph.subgraph(nodes))[0])
    reduced = graph.copy()
    reduction.reduce_mwis(reduced)
    reduced_width = 0
    for nodes in nx.connected_components(reduced):
        if len(nodes) > 1:
            reduced_width = max(reduced_width, reduction.best_tree_decomposition(reduced.subgraph(nodes))[0])
    out.put({"graph_width": width, "reduced_vertices": reduced.number_of_nodes(), "reduced_width": reduced_width,
             "width_seconds": round(time.time() - started, 3)})

    started = time.time()
    independent_set, info = reduction.maximum_independent_set_treewidth(graph, max_width=max_width)
    weight = sum(graph.nodes[v]["weight"] for v in independent_set)
    seconds = round(time.time() - started, 3)
    if weight < target:
        decision = "UNSAT"
    else:
        ok = certify(formula, base, reduction.decode_mis(independent_set, max_variable), stack, variables)
        decision = "SAT" if ok else "UNKNOWN"
    out.put({"weight": weight, "branches": info["branches"], "dp_width": info["width"], "mis_seconds": seconds,
             "decision": decision, "status": "done"})


def run(path, timeout, max_width, gadget):
    row = {"file": os.path.relpath(path, REPO)}
    out = mp.Queue()
    process = mp.Process(target=worker, args=(path, out, max_width, gadget))
    process.start()
    deadline = time.time() + timeout
    while True:
        try:
            row.update(out.get(timeout=max(0.05, min(1.0, deadline - time.time()))))
            if row.get("status") == "done":
                break
        except queue.Empty:
            if not process.is_alive():
                row.setdefault("status", "error")
                break
            if time.time() >= deadline:
                process.terminate()
                row["status"] = f"timeout ({timeout}s)"
                break
    process.join()
    reference = row.get("minisat") if row.get("minisat") in ("SAT", "UNSAT") else row.get("expected")
    decision = row.get("decision")
    if reference and decision in ("SAT", "UNSAT"):
        row["agrees"] = "yes" if decision == reference else "NO"
    return row


def main():
    helper = argparse.ArgumentParser(description="Treewidth and maximum weight independent set of the 1-in-3 3SAT graph.")
    helper.add_argument("-i", "--inputDirectories", nargs="+", default=DEFAULT_DIRECTORIES,
                        help="directories with DIMACS files, relative to the repository root or absolute")
    helper.add_argument("-t", "--timeout", type=float, default=60.0, help="seconds per file (default 60)")
    helper.add_argument("-w", "--maxWidth", type=int, default=15,
                        help="largest tree decomposition width solved by dynamic programming; wider components are "
                             "branched on (default 15)")
    helper.add_argument("-g", "--gadget", choices=["hub", "cycle"], default="hub",
                        help="variable consistency gadget: hub pairs (default) or the long even cycles")
    helper.add_argument("-o", "--output", default=os.path.join(REPO, "car", "treewidth_mis_results.csv"),
                        help="CSV output file")
    args = helper.parse_args()

    rows = []
    for directory in args.inputDirectories:
        directory = directory if os.path.isabs(directory) else os.path.join(REPO, directory)
        if not os.path.isdir(directory):
            print(f"Directory not found: {directory}")
            continue
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            row = run(path, args.timeout, args.maxWidth, args.gadget)
            rows.append(row)
            print(" | ".join(f"{column}={row[column]}" for column in COLUMNS if column in row), flush=True)

    with open(args.output, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})

    decided = [row for row in rows if row.get("decision") in ("SAT", "UNSAT")]
    disagreements = [row for row in rows if row.get("agrees") == "NO"]
    timeouts = [row for row in rows if str(row.get("status", "")).startswith("timeout")]
    print(f"\nFiles: {len(rows)}, decided: {len(decided)}, timeouts: {len(timeouts)}, "
          f"disagreements with MiniSat/file name: {len(disagreements)}")
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()

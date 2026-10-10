# Benchmark experiment for SatyPy: AIM (DIMACS) and SAT Competition 2023/2024 instances.
# The column "minisat" holds the answer of the reference solver chosen with -r (default MiniSat 2.2);
# PRP_40_40 (SAT Competition 2024) needs more than 300 s with MiniSat and 35 s with -r cadical195.
# Author: Frank Vega
#
# For every instance: the expected answer from the file name (AIM "yes"/"no"), MiniSat 2.2 with a
# time limit, and SatyPy (simplification -> 2-SAT -> 3-SAT -> Unique Games -> Vertex Cover ->
# Salvador -> decoding -> verification) with a limit on the size of the Vertex Cover stage.
# Each instance runs in its own process so that peak memory is measured per instance.
#
#   python experiments/run_benchmarks.py -o results.csv benchmarks/file-dimacs-aim benchmarks/sat23 benchmarks/sat24

import argparse
import csv
import multiprocessing
import os
import resource
import threading
import time

from pysat.solvers import Solver

from satypy import algorithm, parser, utils

FIELDS = ["set", "instance", "variables", "clauses", "expected", "minisat", "minisat_seconds", "satypy", "stage",
          "residual_clauses", "three_sat_clauses", "equations", "ug_vertices", "ug_edges", "vc_vertices", "vc_edges",
          "cover", "cover_fraction", "matching_lower_bound", "ratio_upper_bound", "salvador_seconds", "satypy_seconds",
          "verified", "peak_mb"]

VERTICES_PER_CLAUSE, EDGES_PER_CLAUSE = 1895, 11788


def reference_solver(formula, seconds, name="minisat22"):
    """A python-sat solver (default MiniSat 2.2) with a time limit; returns SAT / UNSAT / TIMEOUT."""
    with Solver(name=name, bootstrap_with=formula) as solver:
        timer = threading.Timer(seconds, solver.interrupt)
        timer.start()
        started = time.time()
        answer = solver.solve_limited(expect_interrupt=True)
        timer.cancel()
        return {True: "SAT", False: "UNSAT", None: "TIMEOUT"}[answer], time.time() - started


def run_instance(task):
    path, set_name, minisat_seconds, max_vc_clauses, solver_name = task
    name = os.path.basename(path)
    formula = parser.read(path)
    expected = {True: "SAT", False: "UNSAT"}.get(getattr(formula, "expected_satisfiable", None), "")
    if set_name != "aim":
        expected = ""  # competition file names carry no yes/no label
    row = {"set": set_name, "instance": name, "expected": expected,
           "variables": len({abs(lit) for clause in formula for lit in clause}), "clauses": len(formula)}
    row["minisat"], seconds = reference_solver(formula, minisat_seconds, solver_name)
    row["minisat_seconds"] = round(seconds, 3)
    stats = {}
    started = time.time()
    answer, assignment = algorithm.solve(formula, stats=stats, max_vc_clauses=max_vc_clauses)
    row["satypy_seconds"] = round(time.time() - started, 3)
    row["satypy"] = {True: "SAT", False: "UNSAT", None: "UNKNOWN"}[answer]
    row["verified"] = "" if answer is not True else utils.satisfies(formula, assignment)
    for key in ("stage", "residual_clauses", "three_sat_clauses", "equations", "ug_vertices", "ug_edges",
                "vc_vertices", "vc_edges", "cover", "matching_lower_bound"):
        row[key] = stats.get(key, "")
    if "salvador_seconds" in stats:
        row["salvador_seconds"] = round(stats["salvador_seconds"], 3)
        row["cover_fraction"] = round(stats["cover"] / stats["vc_vertices"], 6)
        row["ratio_upper_bound"] = round(stats["cover"] / stats["matching_lower_bound"], 6)
    elif "three_sat_clauses" in stats:  # projected size of the skipped graph
        row["vc_vertices"] = f"~{VERTICES_PER_CLAUSE * stats['three_sat_clauses']}"
        row["vc_edges"] = f"~{EDGES_PER_CLAUSE * stats['three_sat_clauses']}"
    row["peak_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    return row


def main():
    helper = argparse.ArgumentParser(description="Run SatyPy and MiniSat on directories of DIMACS benchmarks.")
    helper.add_argument("directories", nargs="+")
    helper.add_argument("-o", "--output", default="results.csv")
    helper.add_argument("-j", "--jobs", type=int, default=1, help="parallel processes")
    helper.add_argument("-s", "--minisat_seconds", type=float, default=300.0, help="reference solver time limit")
    helper.add_argument("-r", "--reference", default="minisat22",
                        help="python-sat reference solver, e.g. minisat22 (default) or cadical195")
    helper.add_argument("-m", "--max_vc_clauses", type=int, default=100,
                        help="largest 3-SAT formula sent to the Vertex Cover stage")
    args = helper.parse_args()
    tasks = []
    for directory in args.directories:
        set_name = "aim" if "aim" in directory else os.path.basename(os.path.normpath(directory))
        for name in sorted(utils.get_file_names(directory)):
            if ".cnf" in name:
                tasks.append((os.path.join(directory, name), set_name, args.minisat_seconds, args.max_vc_clauses,
                              args.reference))
    # largest files last so that partial results are useful
    tasks.sort(key=lambda task: os.path.getsize(task[0]))
    with open(args.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        with multiprocessing.Pool(args.jobs, maxtasksperchild=1) as pool:
            for row in pool.imap_unordered(run_instance, tasks):
                writer.writerow(row)
                handle.flush()
                print(row["instance"], row["expected"], row["minisat"], row["satypy"], row["stage"],
                      row["vc_vertices"], row["satypy_seconds"], row["peak_mb"], flush=True)


if __name__ == "__main__":
    main()

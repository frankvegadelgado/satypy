#                          SAT Solver
#                           SATYPY
#                          Frank Vega
#                      April 29th, 2026

import argparse
import os
import time

from . import parser
from . import applogger
from . import utils
from . import algorithm


BRUTE_FORCE_MAX_VARIABLES = 30


def sat_solver(inputFile, verbose=False, timed=False, log=False, bruteForce=False, approximation=False, count=False, max_clauses=100, max_exact=100000):
    """Solves a CNF formula.

    Args:
        inputFile: Input file path.
        verbose: Enable verbose output.
        timed: Enable timer output.
        log: Enable file logging.
        bruteForce: Also solve by exhaustive search (formulas with at most 30 variables).
        approximation: Also solve with a known SAT solver (MiniSat 2.2 via python-sat).
        count: Only state SATISFIABLE / UNSATISFIABLE / UNKNOWN instead of the assignment.
        max_clauses: Largest 3-SAT formula sent to the Unique Games Vertex Cover stage (0: skip it; None: no limit).
        max_exact: Largest 3-SAT formula sent to the exact (Garey-Johnson) Vertex Cover stage (None: no limit).
    """

    logger = applogger.Logger(applogger.FileLogger() if (log) else applogger.ConsoleLogger(verbose))
    started = 0.0
    filename = os.path.basename(inputFile)
    comparing = bruteForce or approximation

    # Read and parse a dimacs file
    utils.println("Pre-processing started", logger)
    if timed:
        started = time.time()

    formula = parser.read(inputFile)

    if timed:
        utils.println(f"Pre-processing done in: {(time.time() - started) * 1000.0} milliseconds", logger)
    else:
        utils.println("Pre-processing done", logger)

    reference = None
    if approximation:
        utils.println("MiniSat started", logger)
        started = time.time()
        reference = utils.minisat_solve(formula)
        utils.println(f"MiniSat done in: {(time.time() - started) * 1000.0} milliseconds", logger)
        utils.output(f"{filename}: (MiniSat) {utils.string_result_format(*reference, count)}", logger, log)

    if bruteForce:
        variables = len({abs(lit) for clause in formula for lit in clause})
        if variables > BRUTE_FORCE_MAX_VARIABLES:
            utils.output(f"{filename}: (Brute Force) skipped, {variables} variables exceed {BRUTE_FORCE_MAX_VARIABLES}",
                         logger, log)
        else:
            utils.println("A solution with an exponential-time complexity started", logger)
            started = time.time()
            brute = utils.brute_force_solve(formula)
            utils.println(f"A solution with an exponential-time complexity done in: {(time.time() - started) * 1000.0} milliseconds", logger)
            utils.output(f"{filename}: (Brute Force) {utils.string_result_format(*brute, count)}", logger, log)
            reference = reference or brute

    # Solving the Boolean Formula
    utils.println("Solving the problem started", logger)
    if timed:
        started = time.time()

    stats = {}
    satisfiability, answer = algorithm.solve(formula, logger, stats=stats, max_vc_clauses=max_clauses,
                                             max_exact_clauses=max_exact)

    if timed:
        utils.println(f"Solving the problem done in: {(time.time() - started) * 1000.0} milliseconds", logger)
    else:
        utils.println("Solving the problem done", logger)

    # Output the solution, preceded by DIMACS comment lines on what the Vertex Cover stages found
    for comment in stats.get("comments", []):
        utils.output(f"{filename}: {comment}" if comparing else comment, logger, verbose or log)
    result = utils.string_result_format(satisfiability, answer, count)
    utils.output(f"{filename}: (SatyPy) {result}" if comparing else result, logger, verbose or log)

    if satisfiability is True and answer is not None and not utils.satisfies(formula, answer):
        utils.output("c ERROR: the SatyPy assignment does not satisfy the formula", logger, verbose or log)
    if reference is not None and satisfiability is not None and satisfiability != reference[0]:
        utils.output("c ERROR: SatyPy disagrees with the reference solver", logger, verbose or log)

    # Compare against benchmark expectation encoded in the file name (yes/no).
    expected = getattr(formula, "expected_satisfiable", None)
    if expected is not None and satisfiability is not None and satisfiability != expected:
        utils.output(
            f"c WARNING: result disagrees with benchmark expectation "
            f"({'SATISFIABLE' if expected else 'UNSATISFIABLE'})",
            logger, verbose or log)


def main():

    # Define the parameters
    helper = argparse.ArgumentParser(prog="saty", description='Solve the Boolean Satisfiability (SAT) problem using a DIMACS file as input.')
    helper.add_argument('-i', '--inputFile', type=str, help='Input file path', required=True)
    helper.add_argument('-a', '--approximation', action='store_true', help='enable comparison with a known SAT solver (MiniSat 2.2 via python-sat)')
    helper.add_argument('-b', '--bruteForce', action='store_true', help='enable comparison with the exponential-time brute-force approach (at most 30 variables)')
    helper.add_argument('-c', '--count', action='store_true', help='only state whether the formula is SATISFIABLE, UNSATISFIABLE or UNKNOWN')
    helper.add_argument('-m', '--max_clauses', type=int, default=100, help='largest 3-SAT formula sent to the Unique Games Vertex Cover stage (about 1,900 vertices, 11,800 edges and 24 MB per clause; 0 skips it; default: 100)')
    helper.add_argument('-e', '--max_exact', type=int, default=100000, help='largest 3-SAT formula sent to the exact (Garey-Johnson) Vertex Cover stage (3 vertices per clause; default: 100000)')
    helper.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    helper.add_argument('-t', '--timer', action='store_true', help='Enable timer output')
    helper.add_argument('-l', '--log', action='store_true', help='Enable file logging')
    helper.add_argument('--version', action='version', version='%(prog)s 0.0.1')

    # Initialize the parameters
    args = helper.parse_args()
    sat_solver(args.inputFile,
               verbose=args.verbose,
               timed=args.timer,
               log=args.log,
               bruteForce=args.bruteForce,
               approximation=args.approximation,
               count=args.count,
               max_clauses=args.max_clauses,
               max_exact=args.max_exact)


if __name__ == "__main__":
    main()

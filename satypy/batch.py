# Created on 04/29/2026
# Author: Frank Vega

import argparse

from . import utils
from . import app

def sat_solver(inputDirectory, verbose=False, timed=False, log=False, bruteForce=False, approximation=False, count=False, max_clauses=100, max_exact=100000):
    """Solves every CNF formula in a directory.

    Args:
        inputDirectory: Input directory path.
        verbose: Enable verbose output.
        timed: Enable timer output.
        log: Enable file logging.
        bruteForce: Also solve by exhaustive search (formulas with at most 30 variables).
        approximation: Also solve with a known SAT solver (MiniSat 2.2 via python-sat).
        count: Only state SATISFIABLE / UNSATISFIABLE / UNKNOWN instead of the assignment.
        max_clauses: Largest 3-SAT formula sent to the Unique Games Vertex Cover stage (0: skip it; None: no limit).
        max_exact: Largest 3-SAT formula sent to the exact (Garey-Johnson) Vertex Cover stage (None: no limit).
    """

    file_names = utils.get_file_names(inputDirectory)

    if file_names:
        for file_name in sorted(file_names):
            inputFile = f"{inputDirectory}/{file_name}"
            print(f"Test: {file_name}")
            app.sat_solver(inputFile, verbose, timed, log, bruteForce, approximation, count, max_clauses, max_exact)

def main():
    
    # Define the parameters
    helper = argparse.ArgumentParser(prog="batch_saty", description='Solve the Boolean Satisfiability (SAT) problem using a directory with DIMACS files as input.')
    helper.add_argument('-i', '--inputDirectory', type=str, help='Input directory path', required=True)
    helper.add_argument('-a', '--approximation', action='store_true', help='enable comparison with a known SAT solver (MiniSat 2.2 via python-sat)')
    helper.add_argument('-b', '--bruteForce', action='store_true', help='enable comparison with the exponential-time brute-force approach (at most 30 variables)')
    helper.add_argument('-c', '--count', action='store_true', help='only state whether each formula is SATISFIABLE, UNSATISFIABLE or UNKNOWN')
    helper.add_argument('-m', '--max_clauses', type=int, default=100, help='largest 3-SAT formula sent to the Unique Games Vertex Cover stage (about 1,900 vertices, 11,800 edges and 24 MB per clause; 0 skips it; default: 100)')
    helper.add_argument('-e', '--max_exact', type=int, default=100000, help='largest 3-SAT formula sent to the exact (Garey-Johnson) Vertex Cover stage (3 vertices per clause; default: 100000)')
    helper.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    helper.add_argument('-t', '--timer', action='store_true', help='Enable timer output')
    helper.add_argument('-l', '--log', action='store_true', help='Enable file logging')
    helper.add_argument('--version', action='version', version='%(prog)s 0.0.3')

    # Initialize the parameters
    args = helper.parse_args()
    sat_solver(args.inputDirectory,
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

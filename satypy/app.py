#                          SAT Solver
#                           ESPERANZA
#                          Frank Vega
#                      April 29th, 2026

import argparse
import time

from . import parser
from . import applogger
from . import utils
from . import algorithm


def sat_solver(inputFile, verbose=False, timed=False, log=False):
    """Solves a CNF formula.

    Args:
        inputFile: Input file path.
        verbose: Enable verbose output.
        timed: Enable timer output.
        log: Enable file logging.
    """
    
    logger = applogger.Logger(applogger.FileLogger() if (log) else applogger.ConsoleLogger(verbose))
    started = 0.0
    
    # Read and parse a dimacs file
    utils.println("Pre-processing started", logger)
    if timed:
        started = time.time()
    
    formula = parser.read(inputFile)
    
    if timed:
        utils.println(f"Pre-processing done in: {(time.time() - started) * 1000.0} milliseconds", logger)
    else:
        utils.println("Pre-processing done", logger)
    
    # Solving the Boolean Formula in Polynomial Time
    utils.println("Solving the problem started", logger)
    if timed:
        started = time.time()

    satisfiability, answer = algorithm.solve(formula)
        
    if timed:
        utils.println(f"Solving the problem done in: {(time.time() - started) * 1000.0} milliseconds", logger)
    else:
        utils.println("Solving the problem done", logger)
  
    # Output the solution
    output = "s UNKNOWN" if (satisfiability is None) else (utils.format_solution(list(answer) + [0]) if (satisfiability) else "s UNSATISFIABLE")
    utils.output(output, logger, verbose or log)

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
    helper.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    helper.add_argument('-t', '--timer', action='store_true', help='Enable timer output')
    helper.add_argument('-l', '--log', action='store_true', help='Enable file logging')
    helper.add_argument('--version', action='version', version='%(prog)s 0.0.1')

    # Initialize the parameters
    args = helper.parse_args()
    sat_solver(args.inputFile,
               verbose=args.verbose,
               timed=args.timer,
               log=args.log)

if __name__ == "__main__":
    main()
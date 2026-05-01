# Created on 04/29/2026
# Author: Frank Vega

import argparse

from . import utils
from . import app

def sat_solver(inputDirectory, verbose=False, timed=False, log=False):
    """Solves a CNF formula.

    Args:
        inputDirectory: Input directory path.
        verbose: Enable verbose output.
        timed: Enable timer output.
        log: Enable file logging.
    """

    file_names = utils.get_file_names(inputDirectory)

    if file_names:
        for file_name in file_names:
            inputFile = f"{inputDirectory}/{file_name}"
            print(f"Test: {file_name}")
            app.sat_solver(inputFile, verbose, timed, log)

def main():
    
    # Define the parameters
    helper = argparse.ArgumentParser(prog="batch_saty", description='Solve the Boolean Satisfiability (SAT) problem using a directory with DIMACS files as input.')
    helper.add_argument('-i', '--inputDirectory', type=str, help='Input directory path', required=True)
    helper.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    helper.add_argument('-t', '--timer', action='store_true', help='Enable timer output')
    helper.add_argument('-l', '--log', action='store_true', help='Enable file logging')
    helper.add_argument('--version', action='version', version='%(prog)s 0.0.1')
    
    # Initialize the parameters
    args = helper.parse_args()
    sat_solver(args.inputDirectory, 
               verbose=args.verbose, 
               timed=args.timer, 
               log=args.log)

if __name__ == "__main__":
    main()
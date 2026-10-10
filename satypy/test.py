# Created on 10/10/2026
# Author: Frank Vega

import argparse
import random
import time

from . import algorithm, applogger, parser, utils


def main():
    helper = argparse.ArgumentParser(prog="test_saty",
                                     description="The SatyPy testing application using randomly generated CNF formulas.")
    helper.add_argument("-d", "--dimension", type=int, help="number of variables of each formula", required=True)
    helper.add_argument("-m", "--clauses", type=int, help="number of clauses (default: round(4.26 * dimension))")
    helper.add_argument("-k", "--width", type=int, default=3, help="literals per clause (default: 3)")
    helper.add_argument("-n", "--num_tests", type=int, default=5, help="number of tests to run")
    helper.add_argument("-g", "--gaps", action="store_true",
                        help="use random non-contiguous variable IDs instead of 1..dimension")
    helper.add_argument("-r", "--seed", type=int, help="random seed")
    helper.add_argument("-a", "--approximation", action="store_true",
                        help="enable comparison with a known SAT solver (MiniSat 2.2 via python-sat)")
    helper.add_argument("-b", "--bruteForce", action="store_true",
                        help="enable comparison with the exponential-time brute-force approach")
    helper.add_argument("-c", "--count", action="store_true",
                        help="only state whether each formula is SATISFIABLE, UNSATISFIABLE or UNKNOWN")
    helper.add_argument("-w", "--write", action="store_true",
                        help="write each generated formula to a DIMACS file in the current directory")
    helper.add_argument("-M", "--max_clauses", type=int, default=100,
                        help="largest 3-SAT formula sent to the Unique Games Vertex Cover stage (0 skips it; default: 100)")
    helper.add_argument("-e", "--max_exact", type=int, default=100000,
                        help="largest 3-SAT formula sent to the exact (Garey-Johnson) Vertex Cover stage (default: 100000)")
    helper.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    helper.add_argument("-l", "--log", action="store_true", help="enable file logging")
    helper.add_argument("--version", action="version", version="%(prog)s 0.0.3")
    args = helper.parse_args()

    logger = applogger.Logger(applogger.FileLogger() if args.log else applogger.ConsoleLogger(args.verbose))
    rng = random.Random(args.seed)
    num_clauses = args.clauses if args.clauses is not None else round(4.26 * args.dimension)
    summary = {"verified": 0, "unsat": 0, "unknown": 0, "disagreements": 0}

    def report(message):
        utils.output(message, logger, args.log)

    for i in range(args.num_tests):
        formula = utils.random_formula(args.dimension, num_clauses, args.width, args.gaps, rng)
        logger.info(f"Creating Formula {i + 1}: {args.dimension} variables, {num_clauses} clauses")
        if args.write:
            filename = f"formula_{i + 1}_{args.seed if args.seed is not None else 'random'}.cnf"
            parser.write(formula, filename)
            report(f"Formula {i + 1} written to file {filename}")

        reference = None
        if args.approximation:
            logger.info("MiniSat started")
            started = time.time()
            reference = utils.minisat_solve(formula)
            logger.info(f"MiniSat done in: {(time.time() - started) * 1000.0} milliseconds")
            report(f"{i + 1}-MiniSat Test: {utils.string_result_format(*reference, args.count)}")

        if args.bruteForce:
            logger.info("A solution with an exponential-time complexity started")
            started = time.time()
            brute = utils.brute_force_solve(formula)
            logger.info(f"A solution with an exponential-time complexity done in: {(time.time() - started) * 1000.0} milliseconds")
            report(f"{i + 1}-Brute Force Test: {utils.string_result_format(*brute, args.count)}")
            reference = reference or brute

        logger.info("Our Algorithm started")
        started = time.time()
        satisfiability, answer = algorithm.solve(formula, logger, max_vc_clauses=args.max_clauses, max_exact_clauses=args.max_exact)
        logger.info(f"Our Algorithm done in: {(time.time() - started) * 1000.0} milliseconds")
        report(f"{i + 1}-SatyPy Test: {utils.string_result_format(satisfiability, answer, args.count)}")

        if satisfiability is True:
            if answer is not None and not utils.satisfies(formula, answer):
                summary["disagreements"] += 1
                report(f"{i + 1}-ERROR: the SatyPy assignment does not satisfy the formula")
            else:
                summary["verified"] += 1
        elif satisfiability is False:
            summary["unsat"] += 1
        else:
            summary["unknown"] += 1
        if reference is not None and satisfiability is not None and satisfiability != reference[0]:
            summary["disagreements"] += 1
            report(f"{i + 1}-ERROR: SatyPy disagrees with the reference solver")

    report(f"Summary: {summary['verified']} SATISFIABLE (verified), {summary['unsat']} UNSATISFIABLE, "
           f"{summary['unknown']} UNKNOWN, {summary['disagreements']} disagreements")


if __name__ == "__main__":
    main()

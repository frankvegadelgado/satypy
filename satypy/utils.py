# Created on 04/29/2026
# Author: Frank Vega

import itertools
import os
import random


def get_file_names(directory):
  """
  Gets a list of all file names within a specified directory.

  Args:
    directory: The path to the directory.

  Returns:
    A list of file names within the directory.
  """
  try:
    return [f for f in os.listdir(directory) if not os.path.isdir(os.path.join(directory, f))]
  except FileNotFoundError:
    print(f"Directory '{directory}' not found.")
    return []

def get_extension_without_dot(filepath):
    """
    Gets the file extension without the dot from an absolute path.

    Args:
        filepath: The absolute path to the file.

    Returns:
        The file extension without the dot, or None if no extension is found.
    """

    filename = os.path.basename(filepath)
    _, ext = os.path.splitext(filename)
    return ext[1:] if ext else None

def println(msg, logger):
    logger.info(msg)

def output(msg, logger, use_logs):
    if use_logs:
        println(msg, logger)
    else:
        print(msg)

def format_solution(answer, max_length=4096):
    lines = []
    # First line: status
    lines.append("s SATISFIABLE")

    if not answer:
        return '\n'.join(lines)

    # Start building the value line
    value_prefix = "v "
    current_line = value_prefix
    for num in map(str, answer):
        # Check if adding the next number would exceed the max line length
        if len(current_line) + len(num) + 1 > max_length:  # +1 for space
            lines.append(current_line)
            current_line = value_prefix
        if current_line != value_prefix:
            current_line += ' '
        current_line += num

    # Add the last value line if it's not empty
    if current_line != value_prefix:
        lines.append(current_line)

    return '\n'.join(lines)

def dimacs_result(satisfiability, answer):
    """DIMACS solution lines: "s SATISFIABLE" plus "v ... 0" (literals sorted by variable; no "v"
    line when satisfiability is certified without an assignment), "s UNSATISFIABLE", or
    "s UNKNOWN"."""
    if satisfiability is None:
        return "s UNKNOWN"
    if not satisfiability:
        return "s UNSATISFIABLE"
    if answer is None:  # satisfiability certified without an assignment (gap rule)
        return "s SATISFIABLE"
    return format_solution([*sorted(answer, key=abs), 0])


def string_result_format(satisfiability, answer, status_only=False):
    """DIMACS solution, or only "SATISFIABLE" / "UNSATISFIABLE" / "UNKNOWN" when status_only."""
    if status_only:
        return {True: "SATISFIABLE", False: "UNSATISFIABLE", None: "UNKNOWN"}[satisfiability]
    return dimacs_result(satisfiability, answer)


def satisfies(formula, literals):
    """True when every clause contains a literal of the assignment."""
    literals = set(literals)
    return all(any(lit in literals for lit in clause) for clause in formula)


def random_formula(num_variables, num_clauses, clause_size=3, gaps=False, rng=random):
    """Random CNF formula with `num_clauses` clauses of `clause_size` distinct variables and
    random signs. With gaps=True the variable IDs are distinct random integers in
    [1, 10 * num_variables] (non-contiguous, in no particular order) instead of 1..num_variables."""
    ids = rng.sample(range(1, 10 * num_variables + 1), num_variables) if gaps else list(range(1, num_variables + 1))
    size = min(clause_size, num_variables)
    return [[v if rng.random() < 0.5 else -v for v in rng.sample(ids, size)] for _ in range(num_clauses)]


def brute_force_solve(formula):
    """Exhaustive search over all assignments of the formula's variables."""
    variables = sorted({abs(lit) for clause in formula for lit in clause})
    for bits in itertools.product((False, True), repeat=len(variables)):
        literals = {v if bit else -v for v, bit in zip(variables, bits, strict=True)}
        if satisfies(formula, literals):
            return True, frozenset(literals)
    return False, None


def minisat_solve(formula):
    """MiniSat 2.2 through python-sat; the model is restricted to the formula's variables."""
    from pysat.solvers import Minisat22  # noqa: PLC0415  (only needed by the test command)
    variables = {abs(lit) for clause in formula for lit in clause}
    with Minisat22(bootstrap_with=formula) as solver:
        if not solver.solve():
            return False, None
        return True, frozenset(lit for lit in solver.get_model() if abs(lit) in variables)

# Created on 04/29/2026
# Author: Frank Vega

import lzma
import bz2
import os
from . import utils


class Formula(list):
    """DIMACS formula with optional benchmark metadata."""

def dimacs(lines):
    """Parses DIMACS CNF content and returns a list of clauses.

    Robust to arbitrary whitespace (tabs, multiple spaces), blank lines and clauses spanning
    several lines. Parsing stops at a SATLIB-style '%' terminator (whatever follows it, such as
    a trailing "0", is not part of the formula). A literal 0 ends the current clause; a 0 that
    ends no literal is the empty clause (which makes the formula unsatisfiable), unless the
    "p cnf n m" header shows that all m clauses have already been read, in which case it is a
    stray terminator and is ignored. Getting this right matters for soundness: dropping an
    empty clause could turn an unsatisfiable formula into a satisfiable one.

    Args:
        lines: A list of lines from the DIMACS file.

    Returns:
        A list of clauses, where each clause is a list of literals.

    Raises:
        ValueError: If a non-integer token appears in a clause line.
    """
    clauses = []
    current = []
    declared = None

    for line in lines:
        line = line.strip()
        if not line or line[0] == 'c':
            continue
        if line[0] == '%':
            break
        if line[0] == 'p':
            fields = line.split()
            if len(fields) >= 4 and fields[1] == 'cnf':
                try:
                    declared = int(fields[3])
                except ValueError:
                    declared = None
            continue
        for token in line.split():
            try:
                literal = int(token)
            except ValueError:
                raise ValueError(f"Invalid DIMACS token: {token!r}")
            if literal == 0:
                if current or declared is None or len(clauses) < declared:
                    clauses.append(current)
                    current = []
            else:
                current.append(literal)

    if current:  # final clause missing its terminating 0
        clauses.append(current)

    return clauses

def read(filepath):
    """Reads a file and returns its lines in DIMACS format.

    Args:
        filepath: The path to the file.
    
    Returns:
        A list of lines in DIMACS format.

    Raises:
        ValueError: If the file extension is not supported.
        FileNotFoundError: If the file is not found.
    """

    try:
        extension = utils.get_extension_without_dot(filepath)
        if extension == 'xz' or extension == 'lzma':
            with lzma.open(filepath, 'rt') as file:
                lines = file.readlines()
        elif extension == 'bz2' or extension == 'bzip2':
            with bz2.open(filepath, 'rt') as file:
                lines = file.readlines()
        else:
            with open(filepath, 'r') as file:
                lines = file.readlines()

        formula = Formula(dimacs(lines))
        name = os.path.basename(str(filepath)).lower()
        if "yes" in name:
            formula.expected_satisfiable = True
        elif "no" in name:
            formula.expected_satisfiable = False
        return formula
    except FileNotFoundError:
        raise FileNotFoundError("File not found: " + str(filepath))
    except UnicodeDecodeError:
        raise ValueError("Invalid file format. Use the -u flag to decompress files before processing: " + str(filepath))


def write(formula, filepath):
    """Writes a list of clauses as a DIMACS CNF file."""
    max_variable = max((abs(lit) for clause in formula for lit in clause), default=0)
    with open(filepath, 'w') as file:
        file.write(f"p cnf {max_variable} {len(formula)}\n")
        for clause in formula:
            file.write(" ".join(map(str, clause)) + " 0\n")

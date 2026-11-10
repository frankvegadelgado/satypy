"""Implied clauses from the XOR constraints of a CNF formula (Gaussian elimination over GF(2)).

A set of ``2^(k-1)`` clauses over the same ``k`` variables whose falsifying assignments all have the same parity is the
equation ``x_1 + ... + x_k = b`` (mod 2): the clauses forbid exactly the assignments of the other parity. The
equations found in a formula, whatever else the formula holds, are a linear system over GF(2). Eliminating it gives

* the proof that the formula is unsatisfiable, when the system is inconsistent;
* equations of at most :data:`IMPLIED_WIDTH` variables (a variable fixed, two variables equal or opposite, three
  variables with a given parity) that every model of the formula satisfies; they are returned as clauses, which the
  formula implies, so adding them changes neither its models nor its satisfiability.

Detecting the equations takes one pass over the clauses. The elimination is stopped when it has spent
:data:`GAUSS_WORK` units (an exclusive-or of two rows costs two units and one more for every 1024 variables of the
system), so that its time is bounded by a constant; then nothing is returned.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Sequence

#: Widest XOR constraint that is looked for (it is written with 2^(k-1) clauses).
MAX_WIDTH: int = 5
#: Widest equation that is returned as clauses.
IMPLIED_WIDTH: int = 3
#: Work after which the elimination is abandoned.
GAUSS_WORK: int = 8_000_000


def find_xors(clauses: Sequence[Sequence[int]]) -> List[tuple]:
    """The XOR constraints written by ``clauses``: a list of ``(variables, rhs)``, ``variables`` the sorted tuple of
    the variables of the constraint and ``rhs`` its right-hand side (the sum of the variables modulo 2)."""
    count: Dict[int, int] = defaultdict(int)
    for clause in clauses:
        count[len(clause)] += 1
    widths = [k for k in range(2, MAX_WIDTH + 1) if count.get(k, 0) >= 2 ** (k - 1)]
    if not widths:
        return []
    wanted = set(widths)
    groups: Dict[tuple, set] = defaultdict(set)
    for clause in clauses:
        if len(clause) not in wanted:
            continue
        ordered = sorted(clause, key=abs)
        groups[tuple(abs(lit) for lit in ordered)].add(tuple(lit < 0 for lit in ordered))
    found = []
    for variables, patterns in groups.items():
        need = 2 ** (len(variables) - 1)
        if len(patterns) < need:
            continue
        for parity in (0, 1):
            # a clause is falsified by the assignment that gives each variable the value of its pattern
            if sum(1 for pattern in patterns if sum(pattern) % 2 == parity) == need:
                found.append((variables, 1 - parity))
    return found


def implied_clauses(clauses: Sequence[Sequence[int]], info: Optional[dict] = None) -> Optional[List[List[int]]]:
    """Clauses implied by the XOR constraints of ``clauses`` that are not clauses of ``clauses`` yet (``[]`` if there
    are none or the elimination was abandoned), or ``None`` if the constraints are inconsistent (the formula is then
    unsatisfiable). ``info`` (optional dict) receives ``xors`` (constraints found), ``rank``, ``work`` and ``implied``."""
    xors = find_xors(clauses)
    if info is not None:
        info.update(xors=len(xors), rank=0, work=0, implied=0)
    if not xors:
        return []
    column = {}
    for variables, _ in xors:
        for v in variables:
            column.setdefault(v, len(column))
    names = sorted(column, key=column.get)
    unit = 2 + len(column) // 1024        # work of one exclusive-or of two rows
    work = 0
    pivots: Dict[int, tuple] = {}         # highest column of a row -> (row, rhs)
    for variables, rhs in xors:
        row = 0
        for v in variables:
            row |= 1 << column[v]
        while row:
            top = row.bit_length() - 1
            if top not in pivots:
                pivots[top] = (row, rhs)
                break
            other, other_rhs = pivots[top]
            row ^= other
            rhs ^= other_rhs
            work += unit
            if work > GAUSS_WORK:
                return []
        else:
            if rhs:
                if info is not None:
                    info.update(work=work)
                return None
    order = sorted(pivots)                # reduced form: a pivot column occurs in its own row only
    pivot_columns = 0
    for top in order:
        pivot_columns |= 1 << top
    for top in order:                     # increasing: the rows of the lower pivots are reduced already
        row, rhs = pivots[top]
        hits = row & pivot_columns & ~(1 << top)
        while hits:
            low = hits & -hits
            other, other_rhs = pivots[low.bit_length() - 1]
            row ^= other
            rhs ^= other_rhs
            hits ^= low
            work += unit
        if work > GAUSS_WORK:
            return []
        pivots[top] = (row, rhs)
    known = {frozenset(clause) for clause in clauses}
    derived: List[List[int]] = []
    for row, rhs in (pivots[top] for top in order):
        if bin(row).count("1") > IMPLIED_WIDTH:
            continue
        involved = [names[i] for i in range(row.bit_length()) if (row >> i) & 1]
        for mask in range(2 ** len(involved)):
            # the assignment with the bits of `mask` forbidden when its parity is not the right-hand side
            if bin(mask).count("1") % 2 != 1 - rhs:
                continue
            clause = [-v if (mask >> i) & 1 else v for i, v in enumerate(involved)]
            if frozenset(clause) not in known:
                derived.append(clause)
    if info is not None:
        info.update(rank=len(pivots), work=work, implied=len(derived))
    return derived

from collections import deque
from math import isqrt
import networkx as nx

def reduce_sat_to_simplified_sat(clauses):
    clause_sets = []
    for c in clauses:
        unique = set(c)
        if not unique:
            return None, None
        if any(-x in unique for x in unique):
            continue
        clause_sets.append(unique)

    occurrences = {}
    counts = {}
    for idx, c in enumerate(clause_sets):
        for lit in c:
            occurrences.setdefault(lit, []).append(idx)
            counts[lit] = counts.get(lit, 0) + 1

    alive = [True] * len(clause_sets)
    committed = set()
    queue = deque()

    def commit_unit(lit):
        if lit in committed:
            return True
        if -lit in committed:
            return False
        committed.add(lit)
        queue.append(lit)
        return True

    def commit_pure(lit):
        if lit not in committed and -lit not in committed:
            committed.add(lit)
            queue.append(lit)

    for c in clause_sets:
        if len(c) == 1 and not commit_unit(next(iter(c))):
            return None, None
    for lit in list(counts):
        if counts.get(-lit, 0) == 0:
            commit_pure(lit)

    while queue:
        lit = queue.popleft()
        for idx in occurrences.get(lit, ()):
            if not alive[idx]:
                continue
            alive[idx] = False
            for other in clause_sets[idx]:
                counts[other] -= 1
                if counts[other] == 0 and counts.get(-other, 0) > 0:
                    commit_pure(-other)

        for idx in occurrences.get(-lit, ()):
            if not alive[idx]:
                continue
            c = clause_sets[idx]
            if -lit not in c:
                continue
            c.discard(-lit)
            counts[-lit] -= 1
            if not c:
                return None, None
            if len(c) == 1 and not commit_unit(next(iter(c))):
                return None, None

    remaining = [list(clause_sets[idx]) for idx, ok in enumerate(alive) if ok]
    if not remaining and not committed and clauses:
        return [], {abs(x) for clause in clauses for x in clause}
    return remaining, committed


# ===========================================================================
# SAT -> Minimum Independent Dominating Set
# ===========================================================================

def mids_bound(num_variables, num_clauses):
    """Least number of copies per clause vertex with bound + N > 2 * sqrt(n) * N, where n = 2N + m * bound is the
    number of vertices of the graph (N variables, m clauses). With C = bound + N the condition reads
    C^2 - 4mN^2 * C - (8N^3 - 4mN^3) > 0, which holds iff C > 2mN^2 + sqrt(4m^2 N^4 + 8N^3 - 4mN^3), so
    bound = 2mN^2 + isqrt(4m^2 N^4 + 8N^3 - 4mN^3) + 1 - N."""
    N, m = num_variables, num_clauses
    return 2 * m * N * N + isqrt(4 * m * m * N ** 4 + 8 * N ** 3 - 4 * m * N ** 3) + 1 - N


def reduce_sat_to_mids(clauses, max_variable):
    """Builds the Minimum Independent Dominating Set graph for a CNF formula (clauses of any width, no
    tautologies, variable IDs at most max_variable).

    Each variable v gives the edge {v, -v}. Each clause gives `bound` = mids_bound(N, m) vertices adjacent to
    its literals (N = number of variables, m = number of clauses); these clause vertices are numbered from
    max_variable + 1. The graph has n = 2N + m * bound vertices and bound + N > 2 * sqrt(n) * N. The formula
    is satisfiable iff the graph has an independent dominating set of N vertices (one endpoint of each edge
    {v, -v}). Otherwise every independent dominating set contains all `bound` copies of some clause vertex: with
    the copies of exactly one clause it also contains an endpoint of each edge {v, -v} (a clause holds at most one
    of v, -v), so it has bound + N vertices; with the copies of two or more clauses it has at least
    2 * bound >= bound + N vertices. So it has more than 2 * sqrt(n) * N vertices.

    Returns (G, N, bound)."""
    G = nx.Graph()
    next_variable = max_variable + 1
    variables = {abs(v) for clause in clauses for v in clause}
    bound = mids_bound(len(variables), len(clauses))
    for v in variables:
        G.add_edge(-v, v)
    for clause in clauses:
        literals = set(clause)
        for _ in range(bound):
            G.add_edges_from((literal, next_variable) for literal in literals)
            next_variable += 1
    return G, len(variables), bound


def decode_mids(independent_dominating_set, max_variable):
    """Reads the literals of an independent dominating set: vertex v (1 <= |v| <= max_variable) is the
    literal v set True."""
    return {v for v in independent_dominating_set if isinstance(v, int) and 1 <= abs(v) <= max_variable}

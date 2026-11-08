from collections import defaultdict, deque

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
# Simplification
# ===========================================================================
# CNF -> Minimum Independent Dominating Set graph (independence only inside the pair of literals of a variable)
# ===========================================================================

def reduce_cnf_to_mids(clauses):
    """Minimum Independent Dominating Set graph of a CNF formula (a list of clauses, lists of non-zero integers).

    The graph has the vertices ("literal", l) for every literal l of a variable of the formula and ("clause", i) for
    every clause i. The two literals of a variable v are joined by the independence edge {("literal", v),
    ("literal", -v)}, and the vertex of a clause is adjacent to the vertices of its literals. No other edge exists.

    An independent dominating set holds at most one literal vertex of each variable and, to dominate the vertices of
    the literals, at least one: exactly one. So it defines an assignment (the literals it holds are true), and it holds
    the vertex of a clause exactly when the assignment leaves the clause without a true literal (a clause vertex is
    adjacent to no other clause vertex, so it is dominated only by a true literal or by itself). Its size is N plus the
    number of clauses that the assignment falsifies: the formula is satisfiable exactly when the graph has an
    independent dominating set of N vertices.

    Returns (G, N), N being the number of variables."""
    G = nx.Graph()
    variables = sorted({abs(lit) for clause in clauses for lit in clause})
    for v in variables:
        G.add_edge(("literal", v), ("literal", -v))
    for i, clause in enumerate(clauses):
        G.add_node(("clause", i))
        G.add_edges_from((("clause", i), ("literal", lit)) for lit in set(clause))
    return G, len(variables)


def decode_mids(independent_dominating_set, max_variable):
    """Literals of an independent dominating set: the literal l of each vertex ("literal", l) with 1 <= |l| <=
    max_variable; a variable that appears with both signs is left out."""
    literals = {vertex[1] for vertex in independent_dominating_set
                if vertex[0] == "literal" and 1 <= abs(vertex[1]) <= max_variable}
    return {lit for lit in literals if -lit not in literals}


def mids_variable_groups(G):
    """The two literal vertices of each variable of a graph of reduce_cnf_to_mids (a single edge). Returns a dict
    variable -> list of vertices."""
    groups = defaultdict(list)
    for vertex in G.nodes:
        if vertex[0] == "literal":
            groups[abs(vertex[1])].append(vertex)
    return dict(groups)

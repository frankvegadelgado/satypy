from collections import deque
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


def reduce_sat_to_3sat(clauses, max_variable):
    three_sat_clauses = []
    next_variable = max_variable + 1
    A, B = next_variable, next_variable + 1
    next_variable += 2
    for clause in clauses:
        unique = list(set(clause))
        L = len(unique)
        if L == 1:
            three_sat_clauses.extend([
                [unique[0],  A,  B], [unique[0], -A,  B],
                [unique[0],  A, -B], [unique[0], -A, -B],
            ])
        elif L == 2:
            three_sat_clauses.extend([unique + [A], unique + [-A]])
        elif L > 3:
            cur = unique
            while len(cur) > 3:
                D = next_variable
                three_sat_clauses.append(cur[:2] + [D])
                cur = [-D] + cur[2:]
                next_variable += 1
            three_sat_clauses.append(cur)
        else:
            three_sat_clauses.append(unique)
    return three_sat_clauses, next_variable - 1


def reduce_3sat_to_nae_3sat(clauses, max_variable):
    new_clauses = []
    next_variable = max_variable + 1
    pivot = next_variable; next_variable += 1
    for clause in clauses:
        new_var = next_variable
        new_clauses.extend([
            [clause[0], clause[1], new_var],
            [clause[2], -new_var, pivot],
        ])
        next_variable += 1
    return new_clauses, next_variable - 1



def reduce_nae_3sat_to_k_s_vc(clauses, max_variable):
    variables = {abs(lit) for clause in clauses for lit in clause}
    next_variable = max_variable + 3
    G = nx.Graph()
    for v in variables:
        G.add_edge(v, -v)

    for clause in clauses:
        x, y, z = tuple(clause)
        a, b, c = next_variable, next_variable + 1, next_variable + 2
        next_variable += 6
        G.add_edge(a, b)
        G.add_edge(b, c)
        G.add_edge(c, a)

        G.add_edge(a, x)
        G.add_edge(b, y)
        G.add_edge(c, z)

        a, b, c = next_variable, next_variable + 1, next_variable + 2
        next_variable += 6
        G.add_edge(a, b)
        G.add_edge(b, c)
        G.add_edge(c, a)

        G.add_edge(a, -x)
        G.add_edge(b, -y)
        G.add_edge(c, -z)

    n = len(variables)
    m = len(clauses)
    # Two triangles per clause (2 chosen vertices each) instead of one.
    k = n + 4 * m
    # Each clause contributes 2 triangle-internal edges (one per triangle)
    s = 2 * m
    return G, k, s


def reduce_k_s_vc_to_exact_subset_sum(G, k, s, max_variable):

    sets = {(u, G.degree(u)) for u in G.nodes()}
    W = G.number_of_edges() + s
    return sets, k, W, max_variable


def reduce_sat_to_exact_subset_sum(clauses, max_variable):
    three_sat, nv = reduce_sat_to_3sat(clauses, max_variable)
    nae_3sat, nv = reduce_3sat_to_nae_3sat(three_sat, nv)
    G, k, s = reduce_nae_3sat_to_k_s_vc(nae_3sat, nv)
    return reduce_k_s_vc_to_exact_subset_sum(G, k, s, nv)
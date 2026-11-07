from collections import Counter, defaultdict, deque
from functools import lru_cache

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
    """Least number of copies per clause vertex with bound + N > 2N * N (N variables): bound = 2N^2 - N + 1.

    Every independent dominating set of the graph has N vertices (one endpoint of each edge {v, -v}, a satisfying
    assignment) or at least bound + N > 2N^2, so on a satisfiable formula its ratio is 1 or larger than 2N = 2 i(G).
    bound >= N + 1, as the structure and the decoding need. The number of clauses `num_clauses` does not enter; the
    graph has n = 2N + m * bound <= 2N + 2mN^2 vertices."""
    N = num_variables
    return 2 * N * N - N + 1


def reduce_sat_to_mids(clauses, max_variable):
    """Builds the Minimum Independent Dominating Set graph for a CNF formula (clauses of any width, no
    tautologies, variable IDs at most max_variable).

    Each variable v gives the edge {v, -v}. Each clause gives `bound` = mids_bound(N, m) vertices adjacent to
    its literals (N = number of variables, m = number of clauses); these clause vertices are numbered from
    max_variable + 1. The graph has n = 2N + m * bound vertices and bound + N > 2N * N. The formula
    is satisfiable iff the graph has an independent dominating set of N vertices (one endpoint of each edge
    {v, -v}). Otherwise every independent dominating set contains all `bound` copies of some clause vertex: with
    the copies of exactly one clause it also contains an endpoint of each edge {v, -v} (a clause holds at most one
    of v, -v), so it has bound + N vertices; with the copies of two or more clauses it has at least
    2 * bound >= bound + N vertices. So it has more than 2N * N vertices (ratio larger than 2N).

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


# ===========================================================================
# SAT -> monotone 3SAT
# ===========================================================================

#: Largest number of extra clauses (each one costs a new variable) that reduce_sat_to_monotone_3sat tries to add to the
#: path of clauses of a clause, instead of complementing variables.
MONOTONE_EXTRA_CLAUSES = 2


@lru_cache(maxsize=None)
def _chain_signs(clauses_in_path, first_sign):
    """Signs of the literal slots of a path of `clauses_in_path` clauses of width at most 3 whose signs alternate, the
    first being `first_sign` (+1 or -1). The first and the last clause have two slots for original literals (three if
    the path is a single clause), the others one. Returns a tuple of (clause index from 1, sign), one per slot."""
    slots = []
    for j in range(1, clauses_in_path + 1):
        sign = first_sign if j % 2 == 1 else -first_sign
        count = 3 if clauses_in_path == 1 else (2 if j in (1, clauses_in_path) else 1)
        slots.extend([(j, sign)] * count)
    return tuple(slots)


def _monotone_options(clause):
    """Ways of writing `clause` (k literals, a positive and b negative) as a path of clauses of width at most 3 with
    alternating signs: max(1, k - 2) + extra clauses, extra in 0..MONOTONE_EXTRA_CLAUSES, the first sign +1 or -1.
    Returns tuples (extra, clauses_in_path, first_sign, positives_to_complement, negatives_to_complement): the clause
    fits when at least that many of its positive (negative) literals are on complemented variables."""
    k = len(clause)
    a = sum(1 for lit in clause if lit > 0)
    b = k - a
    options = []
    for extra in range(MONOTONE_EXTRA_CLAUSES + 1):
        length = max(1, k - 2) + extra
        for first_sign in (1, -1):
            plus = sum(1 for _, sign in _chain_signs(length, first_sign) if sign > 0)
            minus = len(_chain_signs(length, first_sign)) - plus
            options.append((extra, length, first_sign, max(0, a - plus), max(0, b - minus)))
    return options


def _place_literals(clause, length, first_sign, complemented):
    """Puts the literals of `clause` in the slots of the path (`length`, `first_sign`): a literal on a variable that is
    not in `complemented` goes to a slot of its own sign; one on a complemented variable goes to a slot of its own sign
    when one is left, otherwise to the other sign (it is then written with the complement variable). Returns
    (list of (clause index, slot sign, literal), number of literals written with a complement variable), or None if the
    clause does not fit."""
    slots = _chain_signs(length, first_sign)
    positive_slots = [j for j, sign in reversed(slots) if sign > 0]
    negative_slots = [j for j, sign in reversed(slots) if sign < 0]
    rigid_positive = [lit for lit in clause if lit > 0 and lit not in complemented]
    rigid_negative = [lit for lit in clause if lit < 0 and -lit not in complemented]
    if len(rigid_positive) > len(positive_slots) or len(rigid_negative) > len(negative_slots):
        return None
    placed = [(positive_slots.pop(), 1, lit) for lit in rigid_positive]
    placed += [(negative_slots.pop(), -1, lit) for lit in rigid_negative]
    flipped = 0
    for lit in clause:
        if lit > 0 and lit in complemented:
            if positive_slots:
                placed.append((positive_slots.pop(), 1, lit))
            else:
                placed.append((negative_slots.pop(), -1, lit))
                flipped += 1
    for lit in clause:
        if lit < 0 and -lit in complemented:
            if negative_slots:
                placed.append((negative_slots.pop(), -1, lit))
            else:
                placed.append((positive_slots.pop(), 1, lit))
                flipped += 1
    return placed, flipped


def reduce_sat_to_monotone_3sat(clauses, max_variable):
    """CNF -> monotone 3SAT: an equisatisfiable formula whose clauses have at most 3 literals, all positive or all
    negative (variable IDs at most max_variable, no empty clause, no tautology). A satisfying assignment of the result,
    restricted to the variables 1..max_variable, satisfies the original formula, and every satisfying assignment of the
    original formula extends to the result.

    Two kinds of new variables, nothing else is introduced (no padding of short clauses, no copies of clauses):
    - links. A clause of k > 3 literals is split into a path of clauses (l1 l2 y1) (-y1 l3 y2) ... (-y_t l_{k-1} l_k) with
      k - 3 link variables y_j (the standard split). Renaming y_j to its negation in every second link makes the signs
      of the path alternate: link j is written with sign s_j in the clause j and with sign -s_j in the clause j + 1, so
      the link itself is never complemented. Literals go to the slots of their own sign, so the original variables are
      not complemented either, as long as the signs of the clause fit the slots of the path.
    - complements. A variable x whose literal does not fit the sign of its slot gets one complement variable x' (shared
      by all the clauses), written x' instead of -x in a positive clause and -x' instead of x in a negative clause, with
      the clause (-x -x') when x' replaces -x and the clause (x x') when -x' replaces x (only the ones used).
    Every clause chooses the first sign of its path, and 0..MONOTONE_EXTRA_CLAUSES extra clauses (each one extra link
    variable, an extra clause adds slots), that need the fewest new variables given the complements chosen so far;
    the variables to complement are chosen greedily (the most frequent ones) and the extra clauses are then
    re-decided with all the complements known. The least number of complemented variables is a set-covering
    problem, so the result is not claimed to be the minimum over all formulas.

    Returns (monotone_clauses, info); info has "links" (number of link variables), "complements" (dict x -> x' for the
    complement variables that exist) and "new_variables"."""
    formula = [sorted(set(clause), key=abs) for clause in clauses]
    frequency = Counter(abs(lit) for clause in formula for lit in clause)

    # Pass 1: which variables may be complemented.
    complemented = set()
    for clause in formula:
        def missing(option, clause=clause):
            _, _, _, need_positive, need_negative = option
            have_positive = sum(1 for lit in clause if lit > 0 and lit in complemented)
            have_negative = sum(1 for lit in clause if lit < 0 and -lit in complemented)
            return max(0, need_positive - have_positive) + max(0, need_negative - have_negative)

        best = min(_monotone_options(clause), key=lambda option: (option[0] + missing(option), option[0], -option[2]))
        for need, sign in ((best[3], 1), (best[4], -1)):
            side = [abs(lit) for lit in clause if lit * sign > 0]
            lacking = need - sum(1 for variable in side if variable in complemented)
            if lacking > 0:
                candidates = sorted((variable for variable in side if variable not in complemented),
                                    key=lambda variable: (-frequency[variable], variable))
                complemented.update(candidates[:lacking])

    # Pass 2: with all the complements known, the fewest extra clauses and then the fewest complement literals used.
    next_variable = max_variable + 1
    complement = {}
    complement_of_negative = set()   # x' written for -x: needs the clause (-x -x')
    complement_of_positive = set()   # -x' written for x: needs the clause (x x')
    links = 0
    monotone = []

    def write(lit, sign):
        nonlocal next_variable
        if lit * sign > 0:
            return lit
        variable = abs(lit)
        if variable not in complement:
            complement[variable] = next_variable
            next_variable += 1
        if sign > 0:
            complement_of_negative.add(variable)
            return complement[variable]
        complement_of_positive.add(variable)
        return -complement[variable]

    for clause in formula:
        choices = []
        for extra, length, first_sign, _, _ in _monotone_options(clause):
            result = _place_literals(clause, length, first_sign, complemented)
            if result is not None:
                choices.append((extra, result[1], -first_sign, length, first_sign, result[0]))
        _, _, _, length, first_sign, placed = min(choices, key=lambda choice: choice[:3])
        link = [None] + list(range(next_variable, next_variable + length - 1))
        next_variable += length - 1
        links += length - 1
        rows = defaultdict(list)
        for j, sign, lit in placed:
            rows[j].append(write(lit, sign))
        for j in range(1, length + 1):
            sign = first_sign if j % 2 == 1 else -first_sign
            row = rows[j]
            if j > 1:
                row.append(sign * link[j - 1])
            if j < length:
                row.append(sign * link[j])
            monotone.append(row)

    monotone.extend([-variable, -complement[variable]] for variable in sorted(complement_of_negative))
    monotone.extend([variable, complement[variable]] for variable in sorted(complement_of_positive))
    return monotone, {"links": links, "complements": dict(complement), "new_variables": links + len(complement)}


# ===========================================================================
# Monotone 3SAT -> bipartite graph, and its linear program
# ===========================================================================

def reduce_monotone_3sat_to_bipartite(clauses):
    """Bipartite graph of a monotone formula (every clause all positive or all negative).

    Side 0: the positive literals v and the clauses with only negative literals. Side 1: the negative literals -v and
    the clauses with only positive literals. Edges: {v, -v} for each variable (attribute independent=True: exactly one
    of its endpoints is selected), and {literal, clause} for each literal of each clause (independent=False). Literal
    vertices keep the IDs v and -v; the clause vertices are numbered from the largest variable + 1, in the order of the
    clauses. Node attributes: kind ("literal" or "clause"), side (0 or 1)."""
    variables = {abs(lit) for clause in clauses for lit in clause}
    G = nx.Graph()
    for v in sorted(variables):
        G.add_node(v, kind="literal", side=0)
        G.add_node(-v, kind="literal", side=1)
        G.add_edge(v, -v, independent=True)
    next_vertex = max(variables, default=0) + 1
    for clause in clauses:
        positive = clause[0] > 0
        if any((lit > 0) != positive for lit in clause):
            raise ValueError(f"the clause {clause} is not monotone")
        G.add_node(next_vertex, kind="clause", side=1 if positive else 0)
        G.add_edges_from((lit, next_vertex, {"independent": False}) for lit in set(clause))
        next_vertex += 1
    return G


def bipartite_weights(G, clause_weight=1.0, literal_weight=0.0):
    """Weight of every vertex of the bipartite graph: `clause_weight` for the clause vertices and `literal_weight`
    for the literal vertices (a dict vertex -> weight; any dict with a weight per vertex can be given to
    solve_bipartite_lp instead)."""
    return {v: clause_weight if data["kind"] == "clause" else literal_weight for v, data in G.nodes(data=True)}


def solve_bipartite_lp(G, weights=None):
    """Linear program on the bipartite graph, with real variables 0 <= x_v <= 1:

        minimize    sum of weight[v] * x_v
        subject to  x_u + x_v = 1   for every independent edge {v, -v},
                    x_u + x_v >= 1  for every other edge {literal, clause}.

    The constraint matrix is the vertex-edge incidence matrix of a bipartite graph (totally unimodular), so the
    optimum is attained at an integral point. `weights` defaults to bipartite_weights(G). Needs scipy.

    Returns (value, x) with x a dict vertex -> value, or (None, None) if the solver does not find an optimum."""
    import numpy as np  # noqa: PLC0415  (only needed by the linear program)
    from scipy.optimize import linprog  # noqa: PLC0415
    from scipy.sparse import csr_matrix  # noqa: PLC0415

    weights = bipartite_weights(G) if weights is None else weights
    vertices = list(G.nodes)
    index = {v: i for i, v in enumerate(vertices)}
    equality_rows, equality_cols, cover_rows, cover_cols = [], [], [], []
    equalities = covers = 0
    for u, v, data in G.edges(data=True):
        if data["independent"]:
            equality_rows += [equalities, equalities]
            equality_cols += [index[u], index[v]]
            equalities += 1
        else:
            cover_rows += [covers, covers]
            cover_cols += [index[u], index[v]]
            covers += 1
    n = len(vertices)
    result = linprog(
        c=np.array([weights[v] for v in vertices], dtype=float),
        A_ub=csr_matrix((-np.ones(len(cover_rows)), (cover_rows, cover_cols)), shape=(covers, n)) if covers else None,
        b_ub=-np.ones(covers) if covers else None,
        A_eq=csr_matrix((np.ones(len(equality_rows)), (equality_rows, equality_cols)), shape=(equalities, n))
        if equalities else None,
        b_eq=np.ones(equalities) if equalities else None,
        bounds=(0, 1), method="highs")
    if result.status != 0:
        return None, None
    return float(result.fun), {v: float(result.x[index[v]]) for v in vertices}


def decode_bipartite_lp(G, x, tolerance=1e-6):
    """Literals with x = 1 in a solution of solve_bipartite_lp, as a set of non-zero integers, and whether all the
    values are integral (within `tolerance`). With an integral solution it holds exactly one of v, -v for every
    variable v."""
    integral = all(min(value, 1 - value) <= tolerance for value in x.values())
    literals = {v for v, data in G.nodes(data=True) if data["kind"] == "literal" and x[v] > 1 - tolerance}
    return literals, integral

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
# Monotone 3SAT -> bipartite graph
# ===========================================================================

def reduce_monotone_3sat_to_bipartite(clauses):
    """Bipartite graph of a monotone formula (every clause all positive or all negative), with one pair of vertices
    per occurrence of a variable.

    For the variable v and each clause i (numbered from 0) that contains v there are the vertices (v, i) on side 0 and
    (-v, i) on side 1, joined by an independent edge (attribute independent=True: exactly one of its endpoints is
    selected). With i_1 < ... < i_k the clauses of v, the vertices of v form the cycle
    (v, i_1) - (-v, i_1) - (v, i_2) - (-v, i_2) - ... - (-v, i_k) - (v, i_1): the independent edges alternate with the
    edges {(-v, i_j), (v, i_{j+1})} (indices modulo k, absent when k = 1), so that the occurrences of v are all selected
    or all unselected on the side of the positive literals. The clause i is a vertex ("clause", i) joined to (-l, i), the
    negation of the occurrence, for each literal l of the clause: it is on side 0 if the clause is positive (the
    vertices (-v, i) are on side 1) and on side 1 if it is negative (the vertices (v, i) are on side 0). Node
    attributes: kind ("literal" or "clause"), side (0 or 1)."""
    occurrences = defaultdict(list)
    for i, clause in enumerate(clauses):
        for lit in set(clause):
            occurrences[abs(lit)].append(i)
    G = nx.Graph()
    for i, clause in enumerate(clauses):
        positive = clause[0] > 0
        if any((lit > 0) != positive for lit in clause):
            raise ValueError(f"the clause {clause} is not monotone")
        G.add_node(("clause", i), kind="clause", side=0 if positive else 1)
    for v in sorted(occurrences):
        indices = occurrences[v]
        for i in indices:
            G.add_node((v, i), kind="literal", side=0)
            G.add_node((-v, i), kind="literal", side=1)
            G.add_edge((v, i), (-v, i), independent=True)
        if len(indices) > 1:
            for position, i in enumerate(indices):
                G.add_edge((-v, i), (v, indices[(position + 1) % len(indices)]), independent=False)
    for i, clause in enumerate(clauses):
        G.add_edges_from(((-lit, i), ("clause", i), {"independent": False}) for lit in set(clause))
    return G


# ===========================================================================
# Monotone 3SAT -> Minimum Independent Dominating Set
# ===========================================================================

def mids_bound(num_variables, num_occurrences):
    """Number of copies of each clause vertex: bound = 2 * N * L + 1, with N the variables and L the occurrence
    pairs of a monotone formula (L = the vertex pairs (v, i), (-v, i) of reduce_monotone_3sat_to_mids).

    A satisfiable formula has an independent dominating set of L vertices, and an independent dominating set
    with a clause vertex has all `bound` copies of it, so its ratio to L is larger than 2N."""
    return 2 * num_variables * num_occurrences + 1


def reduce_monotone_3sat_to_mids(clauses, copies=None):
    """Minimum Independent Dominating Set graph of a monotone formula (clauses with literals of one sign).

    The occurrences of each variable v form the even cycle of reduce_monotone_3sat_to_bipartite: the vertices
    (v, i) and (-v, i) of every clause i that contains v, the independence edges {(v, i), (-v, i)} and the links
    {(-v, i_j), (v, i_{j+1})}. Each clause i is replaced by `copies` vertices ("clause", i, c), c = 0, ..., copies - 1
    (by default `copies` = mids_bound(N, L)), each adjacent to the vertices (l, i) of the literals l of the clause.
    With copies = 1 the maximum degree of the graph is 3. The graph is
    bipartite (side 0: the vertices (v, i) and the copies of negative clauses; side 1: the vertices (-v, i) and
    the copies of positive clauses).

    If a formula is satisfiable, the vertices (l, i) of its true literals l form an independent dominating set of L
    vertices (one of the two alternating sets of each cycle, and every clause copy has a true literal). An
    independent dominating set that holds a copy of a clause vertex holds all its copies (they have the same
    neighbours), so it has at least `copies` vertices.

    Returns (G, N, L, copies)."""
    G = reduce_monotone_3sat_to_bipartite(clauses)
    G.remove_nodes_from([vertex for vertex, data in G.nodes(data=True) if data["kind"] == "clause"])
    variables = {abs(lit) for clause in clauses for lit in clause}
    occurrences = G.number_of_nodes() // 2
    bound = mids_bound(len(variables), occurrences) if copies is None else copies
    for i, clause in enumerate(clauses):
        side = 1 if clause[0] > 0 else 0
        for copy in range(bound):
            vertex = ("clause", i, copy)
            G.add_node(vertex, kind="clause", side=side)
            G.add_edges_from((vertex, (lit, i)) for lit in set(clause))
    return G, len(variables), occurrences, bound


def decode_mids(independent_dominating_set, max_variable):
    """Literals of an independent dominating set: the literal l of each vertex (l, i) with 1 <= |l| <= max_variable;
    a variable that appears with both signs is left out."""
    literals = {vertex[0] for vertex in independent_dominating_set
                if len(vertex) == 2 and isinstance(vertex[0], int) and 1 <= abs(vertex[0]) <= max_variable}
    return {lit for lit in literals if -lit not in literals}


def mids_variable_groups(G):
    """The vertices (l, i) of each variable of a graph of reduce_monotone_3sat_to_mids: the even cycle (or the single
    edge) of the variable. Returns a dict variable -> list of vertices."""
    groups = defaultdict(list)
    for vertex, data in G.nodes(data=True):
        if data["kind"] == "literal":
            groups[abs(vertex[0])].append(vertex)
    return dict(groups)

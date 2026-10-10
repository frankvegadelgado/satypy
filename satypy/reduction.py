from collections import deque
from fractions import Fraction
from itertools import permutations, product
from math import ceil, gcd

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


# ===========================================================================
# 3SAT -> Unique Games -> unweighted Vertex Cover, and the inverse decoding
# ===========================================================================
#
#   3SAT (exactly three distinct literals per clause, arbitrary variable IDs)
#    |  reduce_3sat_to_parity                  exact clause gadget (10 equations, 2 auxiliaries)
#    v
#   weighted parity instance (three distinct variables per equation)
#    |  reduce_parity_to_matrix_game           tables, exact keys, folding, rank-one test
#    v                                         (OpenAI 2026, Sections 4.2-4.4)
#   weighted translation Unique Game H over K = F_2^ell
#    |  reduce_weighted_game_to_simple_bipartite   rounding + subdivision (Lemma 7.1)
#    v
#   unweighted simple bipartite translation Unique Game B
#    |  parallel_repetition                    B^{(x)t} over F_2^{ell*t}            (Section 7.2)
#    v
#   Unique Game G                              (output form of Theorem 1.1 of the reference)
#    |  reduce_to_strong_left_form             Khot-Regev sequence construction   (Appendix A.1)
#    v
#   strong-left bipartite Unique Game Phi
#    |  reduce_unique_games_to_vertex_cover    p-biased long-code graph           (Khot-Regev 2008)
#    |  reduce_weighted_vertex_cover_to_unweighted   blow-up by multiplicities
#    v
#   unweighted Vertex Cover instance
#
# With p = 1/3 a satisfiable formula yields a cover of at most a 1 - p = 2/3 fraction of the
# vertices (perfectly strongly satisfiable game), so the relevant approximation threshold is
# 1 / (1 - p) = 3/2. The Khot-Regev soundness (every cover >= 1 - epsilon on unsatisfiable
# inputs) holds only for their large parameters; at the small runnable defaults used here the
# instance has no gap and a decoded assignment must always be verified against the formula.
#
# Labels of a translation Unique Game are integers 0 .. 2^dim - 1 (bitmasks of F_2^dim); the
# constraint of an edge (u, v, shift) oriented from u to v reads label(v) == label(u) ^ shift.
#
# References
#   OpenAI Math Team, The Unique Games Conjecture and Optimal Approximation Thresholds
#       (Result Family 102), github.com/openai/math, lean/docs/102.md, 2026.
#   S. Khot, O. Regev, Vertex cover might be hard to approximate to within 2-epsilon,
#       J. Comput. System Sci. 74 (2008) 335-349.
#   F. Vega, Salvador 0.1.0, https://pypi.org/project/salvador/
# ===========================================================================


class UniqueGame:
    """A translation Unique Game over the alphabet F_2^dim.

    edges   : list of (u, v, shift); the constraint is label(v) == label(u) ^ shift.
    weights : list of positive Fractions summing to one, or None for uniform edge occurrences.
    left / right : vertex sets of a bipartite orientation (u in left, v in right), if any.
    """

    def __init__(self, dim, edges, weights=None, left=None, right=None):
        self.dim = dim
        self.edges = list(edges)
        self.weights = None if weights is None else list(weights)
        self.left = None if left is None else set(left)
        self.right = None if right is None else set(right)

    @property
    def alphabet_size(self):
        return 1 << self.dim

    def edge_weight(self, index):
        return Fraction(1, len(self.edges)) if self.weights is None else self.weights[index]

    def is_simple_bipartite(self):
        if self.left is None or self.right is None or self.left & self.right:
            return False
        pairs = set()
        for u, v, _ in self.edges:
            if u not in self.left or v not in self.right or (u, v) in pairs:
                return False
            pairs.add((u, v))
        return True

    def left_weights(self):
        """Total weight of the edges incident to each left vertex."""
        weights = dict.fromkeys(self.left, Fraction(0))
        for i, (u, _, _) in enumerate(self.edges):
            weights[u] += self.edge_weight(i)
        return weights


# ---------------------------------------------------------------------------
# 3SAT -> weighted parity instance
# ---------------------------------------------------------------------------

# Exact clause gadget (found by exhaustive search; none smaller exists). For a clause
# (x or y or z) with fresh auxiliaries w0, w1, some (w0, w1) satisfies exactly 7 of the ten
# equations whenever (x, y, z) != (0, 0, 0), and at most 5 when (x, y, z) = (0, 0, 0).
# Each row is (i, j, k, b): positions 0, 1, 2 are x, y, z and 3, 4 are w0, w1.
PARITY_GADGET = (
    (0, 1, 2, 1), (0, 1, 3, 0), (0, 1, 4, 0), (0, 2, 3, 0), (0, 2, 4, 1),
    (0, 3, 4, 0), (1, 2, 3, 1), (1, 2, 4, 1), (1, 3, 4, 1), (2, 3, 4, 0),
)


def reduce_3sat_to_parity(clauses, max_variable):
    """Exact reduction from 3SAT (three distinct, non-complementary literals per clause) to a
    uniformly weighted parity instance. Variable IDs may be arbitrary positive integers; the
    auxiliaries are max_variable + 1, max_variable + 2, ...
    Returns (equations, weights) with equations (v1, v2, v3, b) on three distinct variables.
    Satisfiable: OPT = 7/10; unsatisfiable: OPT <= 7/10 - 1/(10 m) for m clauses."""
    equations = []
    next_variable = max_variable + 1
    for clause in clauses:
        variables = [abs(lit) for lit in clause] + [next_variable, next_variable + 1]
        negated = [lit < 0 for lit in clause] + [False, False]
        next_variable += 2
        for i, j, k, b in PARITY_GADGET:
            rhs = b ^ int(negated[i]) ^ int(negated[j]) ^ int(negated[k])
            equations.append((variables[i], variables[j], variables[k], rhs))
    return equations, [Fraction(1, len(equations))] * len(equations)


# ---------------------------------------------------------------------------
# Weighted parity instance -> weighted translation Unique Game (matrix game H)
# ---------------------------------------------------------------------------

class LatentGadget:
    """Latent data (V, K, C, mu) of Lemma 3.1 of the reference: V = F_2^dim_v with K = F_2^dim_k
    the low dim_k bits, C : V -> K with C(x ^ k) == C(x) ^ k for k in K, and a rational noise law
    mu on V given as a list of (vector, probability)."""

    def __init__(self, dim_v, dim_k, restore, noise):
        self.dim_v, self.dim_k, self.restore, self.noise = dim_v, dim_k, restore, list(noise)

    def k_part(self, x):
        return x & ((1 << self.dim_k) - 1)

    def w_part(self, x):
        return x >> self.dim_k


def uniform_rank_one_gadget(ell):
    """The ordinary rank-one test: V = K = F_2^ell, C = identity, uniform noise on K."""
    size = 1 << ell
    return LatentGadget(ell, ell, lambda x: x, [(a, Fraction(1, size)) for a in range(size)])


def _table_key(tuple_equations, columns, gadget):
    """Exact key of a table (Section 4.3 of the reference). Returns (vertex, offset): the orbit
    representative (support, W-part of the reduced intercept) and the removed K-part."""
    intercept = columns[0]
    support = []
    for i, (eq_id, (v1, v2, v3, b)) in enumerate(tuple_equations):
        a, d = columns[1 + 2 * i], columns[2 + 2 * i]
        if a == 0 and d == 0:
            continue
        if d == 0:
            support.append(("v", v1, i, a))
        elif a == 0:
            support.append(("v", v2, i, d))
        elif a == d:
            support.append(("v", v3, i, a))
            if b:
                intercept ^= a  # equation (4.3) of the reference
        else:
            support.append(("e", eq_id, i, a, d))
    return (tuple(support), gadget.w_part(intercept)), gadget.k_part(intercept)


def reduce_parity_to_matrix_game(equations, weights, k=1, gadget=None):
    """The matrix game H of Section 4.4 of the reference: sample a k-tuple of equations, a
    uniform table P in Hom(L_U, V), noise a ~ mu and a selector l, and require the restored
    answers of P and P + a l^T to agree. Vertices are key orbits; constraints are translations
    of K. Identical (u, v, shift) occurrences are merged by adding their weights."""
    gadget = gadget or uniform_rank_one_gadget(1)
    m = 1 + 2 * k
    base_weight = Fraction(1, (1 << gadget.dim_v) ** m) * Fraction(1, 1 << m)
    indexed = list(enumerate(equations))
    merged = {}
    for tuple_indices in product(range(len(indexed)), repeat=k):
        tuple_equations = [indexed[i] for i in tuple_indices]
        tuple_weight = base_weight
        for i in tuple_indices:
            tuple_weight *= weights[i]
        for columns in product(range(1 << gadget.dim_v), repeat=m):
            vertex0, offset0 = _table_key(tuple_equations, columns, gadget)
            for a, noise_weight in gadget.noise:
                for selector in range(1 << m):
                    perturbed = tuple(c ^ a if (selector >> j) & 1 else c for j, c in enumerate(columns))
                    vertex1, offset1 = _table_key(tuple_equations, perturbed, gadget)
                    key = (vertex0, vertex1, offset0 ^ offset1)
                    merged[key] = merged.get(key, Fraction(0)) + tuple_weight * noise_weight
    edges = list(merged)
    game = UniqueGame(gadget.dim_k, edges, [merged[e] for e in edges])
    game.gadget, game.equations = gadget, list(equations)
    return game


# ---------------------------------------------------------------------------
# Rounding and subdivision (Lemma 7.1), parallel repetition (Section 7.2)
# ---------------------------------------------------------------------------

def reduce_weighted_game_to_simple_bipartite(game, tau):
    """Round the h occurrence weights to Q = ceil(h / tau) unweighted copies (largest remainder)
    and replace each occurrence u -> v by the path u -- p_e -- q_e -- r_e -- v (identity on the
    first three edges, the original translation on the last). Original vertices ("o", u) and
    q_e are left, p_e and r_e right. val(B) = 1 - (1 - val(H')) / 4 and |val(H') - val(H)| <= tau."""
    tau = Fraction(tau)
    h = len(game.edges)
    Q = ceil(h / tau)
    scaled = [Q * game.edge_weight(i) for i in range(h)]
    counts = [int(s) for s in scaled]
    for i in sorted(range(h), key=lambda i: (-(scaled[i] - counts[i]), i))[:Q - sum(counts)]:
        counts[i] += 1
    left, right, edges = set(), set(), []
    occurrence = 0
    for i, (u, v, shift) in enumerate(game.edges):
        for _ in range(counts[i]):
            p, q, r = ("p", occurrence), ("q", occurrence), ("r", occurrence)
            occurrence += 1
            left.update([("o", u), ("o", v), q])
            right.update([p, r])
            edges.extend([(("o", u), p, 0), (q, p, 0), (q, r, 0), (("o", v), r, shift)])
    return UniqueGame(game.dim, edges, None, left, right)


def parallel_repetition(game, t):
    """The t-fold parallel power over F_2^(dim * t); the shift of a product edge is the
    concatenation of the coordinate shifts."""
    if t == 1:
        return UniqueGame(game.dim, [((u,), (v,), s) for u, v, s in game.edges], None,
                          {(u,) for u in game.left}, {(v,) for v in game.right})
    dim, edges = game.dim, []
    for indices in product(range(len(game.edges)), repeat=t):
        us, vs, shift = [], [], 0
        for position, i in enumerate(indices):
            u, v, s = game.edges[i]
            us.append(u)
            vs.append(v)
            shift |= s << (dim * position)
        edges.append((tuple(us), tuple(vs), shift))
    return UniqueGame(dim * t, edges, None, {e[0] for e in edges}, {e[1] for e in edges})


# ---------------------------------------------------------------------------
# Strong-left form (Khot-Regev sequence construction; Appendix A.1 of the reference)
# ---------------------------------------------------------------------------

def reduce_to_strong_left_form(game, h=1, T=None):
    """Left vertices (x, sequence) with sequence = ((j_1, tag_1), ..., (j_h, tag_h)), pairwise
    distinct tags in range(T) (T >= h, default h); position i joined to (y_{j_i}, tag_i) by the
    shift of occurrence j_i of x. Weighted so that a left vertex followed by a uniform position is
    a uniform edge of the input. A labeling with satisfied fraction f_x at x lifts to one that
    strongly satisfies left weight sum_x (d_x / |E|) f_x^h."""
    T = h if T is None else T
    incident = {}
    for u, v, shift in game.edges:
        incident.setdefault(u, []).append((v, shift))
    total = len(game.edges)
    tag_sequences = list(permutations(range(T), h))
    left, right, edges, weights = set(), set(), [], []
    for x, occurrences in incident.items():
        d = len(occurrences)
        weight = Fraction(d, total * h * d ** h * len(tag_sequences))
        for js in product(range(d), repeat=h):
            for tags in tag_sequences:
                sequence = (x, tuple(zip(js, tags, strict=True)))
                left.add(sequence)
                for j, tag in zip(js, tags, strict=True):
                    y, shift = occurrences[j]
                    right.add((y, tag))
                    edges.append((sequence, (y, tag), shift))
                    weights.append(weight)
    return UniqueGame(game.dim, edges, weights, left, right)


# ---------------------------------------------------------------------------
# Khot-Regev reduction to Vertex Cover and the unweighted blow-up
# ---------------------------------------------------------------------------

def _biased_numerator(subset, R, p):
    """mu_p(S) * denominator(p)^R as an integer, for p = a / b: a^|S| (b - a)^(R - |S|)."""
    size = bin(subset).count("1")
    return p.numerator ** size * (p.denominator - p.numerator) ** (R - size)


def _translate(subset, shift, R):
    image = 0
    for s in range(R):
        if (subset >> s) & 1:
            image |= 1 << (s ^ shift)
    return image


def reduce_unique_games_to_vertex_cover(game, p=Fraction(1, 3)):
    """Khot-Regev graph: vertices (u, S) for every left vertex u and every set S of labels
    (bitmask over range(R)), weight w_u * mu_p(S); (u1, S1) ~ (u2, S2) when u1, u2 share a right
    vertex v and the translates S1 ^ c1, S2 ^ c2 are disjoint. A labeling that strongly
    satisfies left weight 1 - zeta gives the independent set {(u, S) : label(u) in S} of weight
    (1 - zeta) p, i.e. a cover of weight 1 - (1 - zeta) p. Requires 0 < p < 1/2.
    Returns (graph, weights) with weights a dict vertex -> Fraction summing to one."""
    p = Fraction(p)
    R = game.alphabet_size
    subsets = range(1 << R)
    graph = nx.Graph()
    weights = {}
    scale = Fraction(1, p.denominator ** R)
    for u, w_u in game.left_weights().items():
        for S in subsets:
            graph.add_node((u, S))
            weights[(u, S)] = w_u * _biased_numerator(S, R, p) * scale
    incoming = {}
    for u, v, shift in game.edges:
        incoming.setdefault(v, []).append((u, shift))
    for occurrences in incoming.values():
        for index, (u1, c1) in enumerate(occurrences):
            for u2, c2 in occurrences[index:]:
                for S1 in subsets:
                    image1 = _translate(S1, c1, R)
                    for S2 in subsets:
                        if (u1, S1) != (u2, S2) and image1 & _translate(S2, c2, R) == 0:
                            graph.add_edge((u1, S1), (u2, S2))
    return graph, weights


def reduce_weighted_vertex_cover_to_unweighted(graph, weights):
    """Each vertex v becomes n_v = weight(v) * L copies ((v, i)), L the common denominator;
    copies of adjacent vertices are completely joined. Minimum cover = L * minimum weighted
    cover. Returns (blow_up, L)."""
    L = 1
    for w in weights.values():
        L = L * w.denominator // gcd(L, w.denominator)
    multiplicity = {v: int(weights[v] * L) for v in graph.nodes()}
    blow_up = nx.Graph()
    for v in graph.nodes():
        blow_up.add_nodes_from((v, i) for i in range(multiplicity[v]))
    for u, v in graph.edges():
        blow_up.add_edges_from(((u, i), (v, j)) for i in range(multiplicity[u]) for j in range(multiplicity[v]))
    return blow_up, L


def reduce_3sat_to_unweighted_vertex_cover(clauses, max_variable, p=Fraction(1, 3), ell=1, k=1, tau=1, t=1, h=1,
                                           gadget=None):
    """The whole chain. `clauses` must have exactly three distinct, non-complementary literals
    (the output of reduce_sat_to_simplified_sat followed by reduce_sat_to_3sat); max_variable is
    the largest variable ID in use. Returns (graph, info), info holding the intermediate games
    needed by decode_vertex_cover_to_assignment and the size data for logging."""
    p = Fraction(p)
    equations, weights = reduce_3sat_to_parity(clauses, max_variable)
    H = reduce_parity_to_matrix_game(equations, weights, k, gadget or uniform_rank_one_gadget(ell))
    B = reduce_weighted_game_to_simple_bipartite(H, tau)
    G = parallel_repetition(B, t)
    Phi = reduce_to_strong_left_form(G, h)
    weighted, vertex_weights = reduce_unique_games_to_vertex_cover(Phi, p)
    graph, L = reduce_weighted_vertex_cover_to_unweighted(weighted, vertex_weights)
    info = {"matrix_game": H, "bipartite_game": B, "unique_game": G, "strong_left_game": Phi, "p": p,
            "equations": len(equations), "parity": (equations, weights), "first_auxiliary": max_variable + 1,
            "graph": graph, "parameters": {"ell": ell, "k": k, "tau": tau, "t": t, "h": h},
            "gadget": H.gadget, "yes_cover_fraction": 1 - p, "threshold_ratio": 1 / (1 - p)}
    return graph, info


# ---------------------------------------------------------------------------
# The gap rule and the parameters of the reference
# ---------------------------------------------------------------------------

# Section 7.2 of the reference: the repetition exponent must satisfy (1 - 1/10240000)^t <= delta0
# with delta0 <= delta < 1/2, so t >= 10240000 * ln 2 > 7,097,827 even at the weakest soundness.
REFERENCE_MIN_REPETITION = 7_097_828


def reference_parameters_met(parameters, gadget):
    """Necessary conditions for the soundness of the chain (OpenAI 2026, Theorem 1.1, and
    Khot-Regev): the latent alphabet gadget of Lemma 3.1 (not the plain rank-one test), a
    repetition exponent t >= 10,240,000 ln 2, and a sequence length h >= 2 (the soundness of the
    sequence construction is about 1/h). Below these values no lower bound on the covers of
    unsatisfiable formulas is proved, and at the defaults the graph does not depend on
    satisfiability at all. Instances meeting them cannot be stored: the repeated game alone has
    at least 4^7,097,828 edges."""
    return (getattr(gadget, "latent", False) and parameters["t"] >= REFERENCE_MIN_REPETITION
            and parameters["h"] >= 2)


def gap_rule(info, cover_size, no_bound):
    """The decision rule of the gap reduction: if unsatisfiable formulas provably need covers of
    at least `no_bound` (a fraction of the vertices, given by the soundness theorem for the
    parameters used) and Salvador's cover is smaller, the formula is satisfiable; no assignment
    is produced. Returns True when the rule certifies satisfiability, False otherwise. Refuses to
    run with parameters for which no such bound is proved."""
    if not reference_parameters_met(info["parameters"], info["gadget"]):
        raise ValueError("no soundness bound is proved for these parameters")
    return Fraction(cover_size, info["graph"].number_of_nodes()) < Fraction(no_bound)


# ---------------------------------------------------------------------------
# Completeness: from a satisfying assignment to a cover of the chain's graph
# ---------------------------------------------------------------------------

def complete_parity_assignment(equations, assignment, first_auxiliary):
    """Extend `assignment` (variable -> bit on the formula's variables) by the best choice of the
    two auxiliaries of every clause gadget (variables >= first_auxiliary)."""
    assignment = {v: b for v, b in assignment.items() if v < first_auxiliary}
    auxiliaries = list(dict.fromkeys(v for eq in equations for v in eq[:3] if v >= first_auxiliary))
    for index in range(0, len(auxiliaries), 2):
        pair = auxiliaries[index:index + 2]
        local = [eq for eq in equations if any(v in pair for v in eq[:3])]
        best, best_bits = -1, None
        for bits in product((0, 1), repeat=len(pair)):
            trial = dict(assignment)
            trial.update(zip(pair, bits, strict=True))
            count = sum(1 for (a, b, c, rhs) in local if trial.get(a, 0) ^ trial.get(b, 0) ^ trial.get(c, 0) == rhs)
            if count > best:
                best, best_bits = count, bits
        assignment.update(zip(pair, best_bits, strict=True))
    return assignment


def certified_cover_from_assignment(info, literals):
    """The completeness direction of the chain: the labeling induced by an assignment (Lemma 4.3 of
    the reference, lifted through subdivision, repetition and the sequence construction) and the
    Khot-Regev independent set {(u, S): u strongly satisfied, label(u) in S}. Returns the cover of
    the unweighted graph formed by the remaining vertices, and the strongly satisfied left weight
    (the cover has a fraction 1 - p * weight of the vertices)."""
    H, B, G, Phi = info["matrix_game"], info["bipartite_game"], info["unique_game"], info["strong_left_game"]
    equations, _ = info["parity"]
    bits = complete_parity_assignment(equations, {abs(lit): int(lit > 0) for lit in literals}, info["first_auxiliary"])
    gadget = H.gadget
    label_h = {}
    for vertex in {x for edge in H.edges for x in edge[:2]}:
        support, w_intercept = vertex
        value = w_intercept << gadget.dim_k
        for slot in support:
            if slot[0] == "v":
                if bits.get(slot[1], 0):
                    value ^= slot[3]
            else:
                v1, v2 = equations[slot[1]][0], equations[slot[1]][1]
                if bits.get(v1, 0):
                    value ^= slot[3]
                if bits.get(v2, 0):
                    value ^= slot[4]
        label_h[vertex] = gadget.restore(value)
    label_b = {}
    for index in range(0, len(B.edges), 4):
        (u, p_e, _), (q_e, _, _), (_, r_e, _), (v, _, _) = B.edges[index:index + 4]
        label_b[u], label_b[v] = label_h[u[1]], label_h[v[1]]
        label_b[p_e] = label_b[q_e] = label_b[r_e] = label_h[u[1]]
    label_g = {}
    for vertex in {x for edge in G.edges for x in edge[:2]}:
        label = 0
        for position, coordinate in enumerate(vertex):
            label |= label_b[coordinate] << (B.dim * position)
        label_g[vertex] = label
    label_phi = {}
    for u, v, _ in Phi.edges:
        label_phi[u], label_phi[v] = label_g[u[0]], label_g[v[0]]
    violated = {u for u, v, shift in Phi.edges if label_phi[v] != label_phi[u] ^ shift}
    independent = {(u, S) for u in Phi.left if u not in violated
                   for S in range(1 << Phi.alphabet_size) if (S >> label_phi[u]) & 1}
    cover = {node for node in info["graph"].nodes() if node[0] not in independent}
    weights = Phi.left_weights()
    return cover, sum(w for u, w in weights.items() if u not in violated)


# ---------------------------------------------------------------------------
# Decoding a vertex cover back to a truth assignment
# ---------------------------------------------------------------------------

def _plurality(votes):
    """Strict plurality winner of a {value: weight} dict, or None on a tie / no votes."""
    if not votes:
        return None
    ranked = sorted(votes.items(), key=lambda item: -item[1])
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0]


def _vote(table, key, value, weight=1):
    entry = table.setdefault(key, {})
    entry[value] = entry.get(value, 0) + weight


def decode_vertex_cover_to_assignment(info, cover, variables, return_undecided=False):
    """Invert the chain: cover -> Khot-Regev families -> strong-left labels -> G -> B -> H ->
    parity bits. A copy ((u, S), i) outside the cover puts S in the family F_u; u gets the label s
    maximizing the p-biased mass of {S in F_u : s in S}; every later stage takes pluralities.
    The matrix-game labels vote for the bits of their supports: each local assignment whose
    restored table value equals the label gets an equal share of one vote.
    Returns a set of literals over `variables` (undecided variables are set to False), and with
    return_undecided=True also the list of variables that received no decisive vote."""
    Phi, p = info["strong_left_game"], info["p"]
    R = Phi.alphabet_size
    scores = {}
    for (u, S), _ in (node for node in info["graph"].nodes() if node not in cover):
        mass = _biased_numerator(S, R, p)
        for s in range(R):
            if (S >> s) & 1:
                _vote(scores, u, s, mass)
    phi_labels = {u: label for u, votes in scores.items() if (label := _plurality(votes)) is not None}
    right_votes = {}
    for u, v, shift in Phi.edges:
        if u in phi_labels:
            _vote(right_votes, v, phi_labels[u] ^ shift)
    phi_labels.update({v: label for v, votes in right_votes.items() if (label := _plurality(votes)) is not None})

    g_votes = {}
    for vertex, label in phi_labels.items():
        _vote(g_votes, vertex[0], label)
    B = info["bipartite_game"]
    mask = (1 << B.dim) - 1
    b_votes = {}
    for vertex, votes in g_votes.items():
        label = _plurality(votes)
        if label is not None:
            for position, coordinate in enumerate(vertex):
                _vote(b_votes, coordinate, (label >> (B.dim * position)) & mask)
    h_labels = {}
    for vertex, votes in b_votes.items():
        label = _plurality(votes)
        if label is not None and vertex[0] == "o":
            h_labels[vertex[1]] = label

    H = info["matrix_game"]
    gadget, equations = H.gadget, H.equations
    bit_votes = {}
    for (support, w_intercept), label in h_labels.items():
        slots = []
        for slot in support:
            if slot[0] == "v":
                slots.append(((slot[1], slot[3]),))
            else:
                v1, v2 = equations[slot[1]][0], equations[slot[1]][1]
                slots.append(((v1, slot[3]), (v2, slot[4])))
        local_variables = list(dict.fromkeys(var for slot in slots for var, _ in slot))
        if not local_variables:
            continue
        matches = []
        for bits in product((0, 1), repeat=len(local_variables)):
            local = dict(zip(local_variables, bits, strict=True))
            value = w_intercept << gadget.dim_k
            for slot in slots:
                for var, slope in slot:
                    if local[var]:
                        value ^= slope
            if gadget.restore(value) == label:
                matches.append(local)
        for local in matches:
            for var, bit in local.items():
                _vote(bit_votes, var, bit, Fraction(1, len(matches)))
    literals = {v if _plurality(bit_votes.get(v, {})) == 1 else -v for v in variables}
    if return_undecided:
        return literals, [v for v in variables if _plurality(bit_votes.get(v, {})) is None]
    return literals


def approximate_vertex_cover(graph):
    """Salvador 0.1.0 (worst-case ratio at most 2). Returns (cover, matching_lower_bound)."""
    from salvador.algorithm import find_vertex_cover  # noqa: PLC0415  (lazy: keeps scipy out of import time)
    return set(find_vertex_cover(graph)), len(nx.maximal_matching(graph))


# ---------------------------------------------------------------------------
# Exact reduction 3SAT -> Vertex Cover (Karp; Garey and Johnson)
# ---------------------------------------------------------------------------

def reduce_3sat_to_exact_vertex_cover(clauses):
    """Karp's reduction in the form of Garey and Johnson: an edge (x, -x) for every variable,
    a triangle for every clause, and an edge from each corner to the vertex of its literal.
    Vertices are ("lit", literal) and ("cl", clause index, position). The formula, with n
    variables and m clauses of three distinct literals, is satisfiable if and only if the graph
    has a vertex cover of size n + 2m; every cover has at least n + 2m vertices.
    Returns (graph, n + 2m)."""
    graph = nx.Graph()
    variables = {abs(lit) for clause in clauses for lit in clause}
    graph.add_edges_from((("lit", v), ("lit", -v)) for v in variables)
    for index, clause in enumerate(clauses):
        corners = [("cl", index, position) for position in range(3)]
        graph.add_edges_from([(corners[0], corners[1]), (corners[1], corners[2]), (corners[0], corners[2])])
        graph.add_edges_from((corner, ("lit", lit)) for corner, lit in zip(corners, clause, strict=True))
    return graph, len(variables) + 2 * len(clauses)


def decode_exact_vertex_cover(cover):
    """The literals whose vertex lies in the cover (and whose complement does not). For a cover
    of size exactly n + 2m this is a satisfying assignment: the cover holds one vertex of every
    variable edge and two corners of every triangle, and the edge from the third corner forces
    its literal into the cover."""
    literals = {node[1] for node in cover if node[0] == "lit"}
    return {lit for lit in literals if -lit not in literals}

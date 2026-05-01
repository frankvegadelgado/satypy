# Created on 04/29/2026  (weighted PTAS + certificate completion 05/01/2026)
# Author: Frank Vega

import itertools

from . import reduction
from . import baker


def _complete_and_check(sat_instance, base, partial_cert, max_variable):
    """Enumerate undecided original variables and return the first SAT certificate.

    The PTAS IDS may not encode a truth value for every original variable — this
    happens when neither double(+v) nor double(-v) is selected (both are dominated
    by their negative-complement pair nodes instead). For those undecided variables
    we try all 2^k truth-value combinations (k = number of undecided variables).

    Both the direct candidate and its NAE-3MSAT complement are tried for each
    combination, exploiting the symmetry: if A is a NAE-satisfying assignment,
    so is ¬A, and one of the two maps to a satisfying assignment of the original
    SAT formula.

    Args:
        sat_instance:  Original CNF formula (list of lists of non-zero ints).
        base:          Literals forced True by Stage-0 simplification.
        partial_cert:  Literals extracted from the PTAS IDS for DECIDED variables.
        max_variable:  Largest variable index in the original formula.

    Returns:
        (True,  frozenset_of_literals)  if any completion satisfies the formula,
        (False, None)                   otherwise.
    """
    formula = [frozenset(clause) for clause in sat_instance]

    decided   = {abs(x) for x in partial_cert}
    undecided = [v for v in range(1, max_variable + 1) if v not in decided]

    for bits in itertools.product((1, -1), repeat=len(undecided)):
        extra = {bits[i] * undecided[i] for i in range(len(undecided))}
        for candidate in (base | partial_cert | extra,
                          base | {-x for x in partial_cert} | extra):
            if all(clause & candidate for clause in formula):
                return True, frozenset(candidate)

    return False, None


def solve(formula):
    """Decides satisfiability of a CNF formula via the weighted MIDS reduction.

    Reduction pipeline
    ──────────────────
      Stage 0  SAT → simplified SAT  (unit propagation, pure literals)
      Stage 1  simplified SAT → 3SAT
      Stage 2  3SAT → NAE-3SAT
      Stage 3  NAE-3SAT → NAE-3MSAT  (monotone, no negations)
      Stage 4  NAE-3MSAT → weighted planar MIDS
                 Variable nodes {v, −v}: weight 1
                 Clause hub nodes:       weight W = 3·M
                 _maximal_planar_subgraph guarantees a planar graph.
      Stage 5  Baker (1+ε)-PTAS on the planar MIDS graph, using weights
      Stage 6  Certificate extraction from VARIABLE NODES ONLY
      Stage 7  Complete undecided variables and verify against original formula

    Why hub nodes are excluded from certificate extraction
    ──────────────────────────────────────────────────────
      With W = 3M and N_pairs ≤ 3M, any hub-inclusive IDS has weighted cost
      ≥ N_pairs + W ≥ 2·N_pairs > 1.1·N_pairs = (1+ε)·OPT_sat.
      In theory the PTAS should never select hubs. In practice, Baker's PTAS
      resolves hub domination component-locally; when a hub's literal neighbours
      lie in different BFS components (removed layers), the local DP may add the
      hub to the IDS instead of waiting for the literal to appear in another
      component. We therefore discard all hub nodes (weight W) from the PTAS
      solution before certificate extraction.

    Undecided variables
    ───────────────────
      Even after discarding hubs, some original variable v may have NEITHER
      double(+v) NOR double(-v) in the remaining IDS — both are dominated by
      their respective negative-complement pair nodes rather than by being
      selected themselves. _complete_and_check enumerates the 2^k truth-value
      combinations for the k undecided variables (typically k is very small)
      and returns the first combination that satisfies the original formula.

    UNSAT detection
    ───────────────
      If the formula is unsatisfiable, every variable assignment leaves at least
      one clause violated. _complete_and_check exhausts all 2^k completions
      without finding a satisfying one, and returns (False, None).

    Args:
        formula: CNF formula as a list of clauses (lists of non-zero ints).

    Returns:
        (True,  frozenset_of_assigned_literals) if satisfiable,
        (False, None)                           if unsatisfiable.
    """
    if not formula:
        return True, frozenset()

    max_variable = max(abs(lit) for clause in formula for lit in clause)

    # ── Stage 0: Simplification ──────────────────────────────────────────────
    clauses, solution = reduction.reduce_sat_to_simplified_sat(formula)

    if not clauses:
        if solution:
            return _complete_and_check(formula, solution, set(), max_variable)
        return False, None

    # ── Stages 1–4: SAT → weighted planar MIDS ──────────────────────────────
    G, weights, opt_sat, P, eps = reduction.reduce_sat_to_mids(
        clauses, max_variable, epsilon=0.1)

    # ── Stage 5: Baker (1+ε)-PTAS ────────────────────────────────────────────
    nodes     = list(G.nodes())
    mapping   = {u: k for k, u in enumerate(nodes)}
    unmapping = {k: u for u, k in mapping.items()}

    adj = {mapping[v]: {mapping[w] for w in G[v]} for v in G}
    wts = {mapping[v]: weights[v] for v in G}

    sol = baker.baker_ptas_ids_weighted(adj, weights=wts, epsilon=eps)

    # ── Stage 6: Certificate extraction — variable nodes only ────────────────
    # Discard hub nodes (weight W): they may have entered the IDS due to
    # Baker's component-local domination heuristic, not because they encode
    # the satisfying assignment. Only weight-1 (variable) nodes carry the
    # literal information needed for the certificate.
    W = P  # hub weight stored as P by reduce_sat_to_mids
    ids_nodes = {unmapping[k] for k in sol if weights.get(unmapping[k], 0) != W}

    # For each original variable v, check whether double(+v)=2v or
    # double(-v)=2v+1 was selected in the variable-node IDS.
    partial_cert = set()
    for v in range(1, max_variable + 1):
        if 2 * v in ids_nodes:
            partial_cert.add(v)
        elif 2 * v + 1 in ids_nodes:
            partial_cert.add(-v)
        # If neither: v is undecided; _complete_and_check will enumerate it.

    # Remove certificate literals that contradict forced base literals.
    partial_cert -= {-x for x in solution}

    # ── Stage 7: Complete undecided variables and verify ─────────────────────
    return _complete_and_check(formula, solution, partial_cert, max_variable)
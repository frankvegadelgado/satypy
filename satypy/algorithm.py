import time
from fractions import Fraction

from . import reduction, utils


def check(sat_instance, base, answer):
    variables = {abs(lit) for clause in sat_instance for lit in clause}
    for candidate in (base | answer,
                      base | {-x for x in answer},
                      set(base)):
        if any(-lit in candidate for lit in candidate):
            continue
        assigned = {abs(lit) for lit in candidate}
        rest = [v for v in variables if v not in assigned]
        for completion in (set(rest), {-v for v in rest}):
            completed = candidate | completion
            if all(any(lit in completed for lit in clause)
                   for clause in sat_instance):
                return True, frozenset(completed)
    return False, None


def _solve_two_sat(clauses):
    adjacency = {}
    reverse_adjacency = {}
    nodes = set()

    def add_edge(u, v):
        adjacency.setdefault(u, []).append(v)
        reverse_adjacency.setdefault(v, []).append(u)

    for clause in clauses:
        lits = list(clause)
        a = lits[0]
        b = lits[1] if len(lits) > 1 else lits[0]
        nodes.update((a, -a, b, -b))
        add_edge(-a, b)
        add_edge(-b, a)

    visited = set()
    finish_order = []
    for start in nodes:
        if start in visited:
            continue
        visited.add(start)
        stack = [(start, iter(adjacency.get(start, ())))]
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append((nxt, iter(adjacency.get(nxt, ()))))
                    advanced = True
                    break
            if not advanced:
                finish_order.append(node)
                stack.pop()

    comp = {}
    comp_id = 0
    for start in reversed(finish_order):
        if start in comp:
            continue
        comp[start] = comp_id
        stack = [start]
        while stack:
            node = stack.pop()
            for nxt in reverse_adjacency.get(node, ()):
                if nxt not in comp:
                    comp[nxt] = comp_id
                    stack.append(nxt)
        comp_id += 1

    variables = {abs(lit) for lit in nodes}
    for v in variables:
        if comp[v] == comp[-v]:
            return False, None

    assignment = {v if comp[v] > comp[-v] else -v for v in variables}
    return True, assignment

def solve(formula, logger=None, p=Fraction(1, 3), stats=None, max_vc_clauses=None, max_exact_clauses=100000,
          gap_no_bound=None):
    """Decide a CNF formula; see _solve. This wrapper is the final certification gate: a
    SATISFIABLE answer is returned only if the assignment is consistent (no variable with both
    signs) and contains a literal of every clause of the original formula; otherwise the
    answer is downgraded to UNKNOWN. UNSATISFIABLE can only come from the exact stages of
    _solve (an empty clause after unit propagation, or an unsatisfiable residual 2-SAT formula).
    The only SATISFIABLE answer without an assignment comes from the gap rule of the
    OpenAI/Khot-Regev chain, which runs only with a proved soundness bound (gap_no_bound) and
    parameters meeting the reference (reduction.reference_parameters_met)."""
    stats = {} if stats is None else stats
    stats["comments"] = []
    satisfiability, answer = _solve(formula, logger, p, stats, max_vc_clauses, max_exact_clauses, gap_no_bound)
    if satisfiability is True and answer is None:
        return (True, None) if stats.get("stage") == "gap rule" else (None, None)
    if satisfiability is True:
        literals = set(answer)
        if any(-lit in literals for lit in literals) or not utils.satisfies(formula, literals):
            if logger is not None:
                utils.println("Certification failed: the assignment is rejected", logger)
            return None, None
    return satisfiability, answer


def _solve(formula, logger=None, p=Fraction(1, 3), stats=None, max_vc_clauses=None, max_exact_clauses=100000,
           gap_no_bound=None):
    """Decide a CNF formula given as a list of clauses (lists of non-zero integers; variable IDs
    need not be 1..n, contiguous or sorted).

    1. reduce_sat_to_simplified_sat: unit propagation and pure literals (sound UNSAT on conflicts);
    2. residual 2-SAT: solved exactly by _solve_two_sat (sound UNSAT);
    3. otherwise reduce_sat_to_3sat, then Karp's exact reduction to Vertex Cover (Garey-Johnson
       graph, 2n + 3m vertices): if Salvador's cover has exactly n + 2m vertices it is optimal and
       decodes into a satisfying assignment;
    4. otherwise the 3SAT -> Unique Games -> unweighted Vertex Cover chain, a cover from Salvador,
       decoding of the cover into an assignment, and verification.

    Returns (True, assignment) with a verified satisfying assignment (frozenset of literals),
    (False, None) when stages 1-2 prove unsatisfiability, or (None, None) when the decoded
    assignment does not satisfy the formula: no unsatisfiability is ever inferred from the
    vertex cover, because the Khot-Regev gap does not hold at the parameters used here.
    If `stats` is a dict it receives the deciding stage and the sizes of every instance built.
    With max_exact_clauses / max_vc_clauses set, stage 3 / stage 4 is skipped when the 3-SAT
    formula has more clauses (stage 3 builds 3 vertices per clause, stage 4 about 1,900 vertices
    and 11,800 edges per clause); max_vc_clauses = 0 disables stage 4.
    """
    stats = {} if stats is None else stats
    stats.setdefault("comments", [])

    def log(message):
        if logger is not None:
            utils.println(message, logger)

    stats["stage"] = "empty"
    if not formula:
        return True, frozenset()
    if any(len(clause) == 0 for clause in formula):
        stats["stage"] = "empty clause"
        log("The formula contains the empty clause")
        return False, None
    variables = sorted({abs(lit) for clause in formula for lit in clause})
    max_variable = variables[-1]
    log(f"Formula: {len(variables)} variables, {len(formula)} clauses")

    stats.update(variables=len(variables), clauses=len(formula), stage="simplification")
    clauses, solution = reduction.reduce_sat_to_simplified_sat(formula)
    if clauses is None:
        log("Simplification found a conflict")
        return False, None
    log(f"Simplification: {len(clauses)} clauses left, {len(solution)} literals committed")
    stats.update(residual_clauses=len(clauses), committed=len(solution))
    if not clauses:
        ok, assignment = check(formula, solution, set())
        return (True, assignment) if ok else (None, None)

    if all(len(clause) <= 2 for clause in clauses):
        log("Residual formula is 2-SAT")
        stats["stage"] = "2-SAT"
        sat2, assignment = _solve_two_sat(clauses)
        if not sat2:
            return False, None
        ok, checked = check(formula, solution, set(assignment))
        return (True, checked) if ok else (None, None)

    three_sat, three_max = reduction.reduce_sat_to_3sat(clauses, max_variable)
    stats["three_sat_clauses"] = len(three_sat)
    log(f"3-SAT: {len(three_sat)} clauses, largest variable {three_max}")

    if max_exact_clauses is None or len(three_sat) <= max_exact_clauses:
        stats["stage"] = "exact vertex cover"
        exact_graph, target = reduction.reduce_3sat_to_exact_vertex_cover(three_sat)
        log(f"Exact Vertex Cover instance: {exact_graph.number_of_nodes()} vertices, {exact_graph.number_of_edges()} edges, "
            f"satisfiable iff a cover of {target} vertices exists")
        started = time.time()
        exact_cover, _ = reduction.approximate_vertex_cover(exact_graph)
        stats.update(exact_vertices=exact_graph.number_of_nodes(), exact_edges=exact_graph.number_of_edges(),
                     exact_target=target, exact_cover=len(exact_cover), exact_seconds=time.time() - started)
        log(f"Salvador cover: {len(exact_cover)} vertices ({len(exact_cover) - target} above n + 2m)")
        if len(exact_cover) > target:
            stats["comments"].append(
                f"c Karp graph: {exact_graph.number_of_nodes()} vertices; Salvador cover: {len(exact_cover)} vertices, "
                f"{len(exact_cover) - target} above the bound n + 2m = {target} (satisfiability not determined)")
        if len(exact_cover) == target:
            decoded = reduction.decode_exact_vertex_cover(exact_cover)
            ok, full = check(formula, solution, {lit for lit in decoded if abs(lit) <= max_variable})
            if ok:
                log("Decoded assignment verified")
                return True, full

    if max_vc_clauses == 0:
        return None, None
    stats["stage"] = "unique games vertex cover"
    if max_vc_clauses is not None and len(three_sat) > max_vc_clauses:
        stats["stage"] = "unique games vertex cover skipped (size)"
        log(f"Vertex Cover stage skipped: {len(three_sat)} 3-SAT clauses exceed the limit {max_vc_clauses}")
        return None, None
    graph, info = reduction.reduce_3sat_to_unweighted_vertex_cover(three_sat, three_max, p=p)
    log(f"Parity instance: {info['equations']} equations; Unique Game: "
        f"{len(info['unique_game'].left) + len(info['unique_game'].right)} vertices, "
        f"{len(info['unique_game'].edges)} edges over an alphabet of size {info['unique_game'].alphabet_size}")
    log(f"Vertex Cover instance: {graph.number_of_nodes()} vertices, {graph.number_of_edges()} edges "
        f"(satisfiable formulas admit covers of fraction {info['yes_cover_fraction']}; "
        f"threshold ratio {info['threshold_ratio']})")

    stats.update(equations=info["equations"], ug_vertices=len(info["unique_game"].left) + len(info["unique_game"].right),
                 ug_edges=len(info["unique_game"].edges), vc_vertices=graph.number_of_nodes(),
                 vc_edges=graph.number_of_edges())
    started = time.time()
    cover, lower_bound = reduction.approximate_vertex_cover(graph)
    stats.update(salvador_seconds=time.time() - started, cover=len(cover), matching_lower_bound=lower_bound)
    log(f"Salvador cover: {len(cover)} vertices, fraction {Fraction(len(cover), graph.number_of_nodes())}, "
        f"ratio <= {Fraction(len(cover), lower_bound) if lower_bound else 1}")

    fraction = Fraction(len(cover), graph.number_of_nodes())
    if gap_no_bound is not None and reduction.gap_rule(info, len(cover), gap_no_bound):
        stats["stage"] = "gap rule"
        log("Gap rule: the cover is below the proved bound for unsatisfiable formulas")
        return True, None
    if not reduction.reference_parameters_met(info["parameters"], info["gadget"]):
        stats["comments"].append(
            f"c OpenAI/Khot-Regev chain: {graph.number_of_nodes()} vertices; Salvador cover: {len(cover)} vertices "
            f"(fraction {fraction}; satisfiable formulas admit {info['yes_cover_fraction']}); gap rule inactive: "
            f"parameters t={info['parameters']['t']}, h={info['parameters']['h']}, rank-one gadget are below the "
            f"reference's (t >= {reduction.REFERENCE_MIN_REPETITION:,}, h >= 2, latent gadget)")

    original = [v for v in variables if v not in {abs(lit) for lit in solution}]
    decoded = reduction.decode_vertex_cover_to_assignment(info, cover, original)
    ok, full = check(formula, solution, decoded)
    if ok:
        log("Decoded assignment verified")
        return True, full
    log("Decoded assignment does not satisfy the formula")
    return None, None

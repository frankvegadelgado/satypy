import time

from siriaisa.algorithm import find_independent_dominating_set

from . import reduction, utils

CANDIDATES = ("the assignment", "the complement of the assignment", "the committed literals only")
COMPLETIONS = ("other variables True", "other variables False")


def check(sat_instance, base, answer, report=None):
    """Look for a satisfying assignment among a few candidates built from `answer`: the answer itself,
    its complement, and the committed literals alone, each completed with all remaining variables
    True or all False. If `report` is a dict it receives which candidate and completion succeeded and
    how many variables the completion had to fill."""
    variables = {abs(lit) for clause in sat_instance for lit in clause}
    for index, candidate in enumerate((base | answer, base | {-x for x in answer}, set(base))):
        if any(-lit in candidate for lit in candidate):
            continue
        assigned = {abs(lit) for lit in candidate}
        rest = [v for v in variables if v not in assigned]
        for which, completion in enumerate((set(rest), {-v for v in rest})):
            completed = candidate | completion
            if all(any(lit in completed for lit in clause)
                   for clause in sat_instance):
                if report is not None:
                    report.update(candidate=CANDIDATES[index], completion=COMPLETIONS[which] if rest else None,
                                  filled=len(rest))
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

def solve(formula, logger=None, stats=None):
    """Decide a CNF formula; see _solve. This wrapper is the final certification gate: a
    SATISFIABLE answer is returned only if the assignment is consistent (no variable with both
    signs) and contains a literal of every clause of the original formula; otherwise the
    answer is downgraded to UNKNOWN."""
    stats = {} if stats is None else stats
    stats["comments"] = []
    satisfiability, answer = _solve(formula, logger, stats)
    if satisfiability is True:
        if answer is None:
            return None, None
        literals = set(answer)
        if any(-lit in literals for lit in literals) or not utils.satisfies(formula, literals):
            if logger is not None:
                utils.println("Certification failed: the assignment is rejected", logger)
            return None, None
    return satisfiability, answer


def _solve(formula, logger=None, stats=None):
    """Decide a CNF formula given as a list of clauses (lists of non-zero integers; variable IDs
    need not be 1..n, contiguous or sorted).

    1. reduce_sat_to_simplified_sat: unit propagation and pure literals (UNSAT on conflicts);
    2. residual 2-SAT: solved exactly by _solve_two_sat;
    3. otherwise reduce_sat_to_mids (the residual formula with N variables and m clauses -> a graph
       with n vertices: an edge {v, -v} per variable and bound copies of a vertex per clause, adjacent
       to its literals, with bound + N > 2 * sqrt(n) * N) and Siriaisa's independent dominating set S:
       - |S| < bound: S has no clause vertex, so it is one endpoint of each edge {v, -v} and it is
         decoded into an assignment, which is verified (SATISFIABLE);
       - |S| > 2 * sqrt(n) * N: UNSATISFIABLE under the conjecture that Siriaisa's approximation
         ratio is at most 2 * sqrt(n) (a satisfiable formula has a MIDS of N vertices, an
         unsatisfiable one has none smaller than bound + N);
       - otherwise UNKNOWN.
       Comment lines in stats["comments"] report what the stage found.

    Returns (True, assignment) with a verified satisfying assignment (frozenset of literals),
    (False, None), or (None, None).
    If `stats` is a dict it receives the deciding stage and the sizes of the instances built.
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
        stats["comments"].append("c decided by: the empty clause")
        return False, None
    variables = sorted({abs(lit) for clause in formula for lit in clause})
    max_variable = variables[-1]
    log(f"Formula: {len(variables)} variables, {len(formula)} clauses")

    stats.update(variables=len(variables), clauses=len(formula), stage="simplification")
    clauses, solution = reduction.reduce_sat_to_simplified_sat(formula)
    if clauses is None:
        log("Simplification found a conflict")
        stats["comments"].append("c decided by: simplification (unit propagation found a conflict)")
        return False, None
    log(f"Simplification: {len(clauses)} clauses left, {len(solution)} literals committed")
    stats.update(residual_clauses=len(clauses), committed=len(solution))
    if not clauses:
        ok, assignment = check(formula, solution, set())
        if ok:
            stats["comments"].append("c decided by: simplification (unit propagation and pure literals)")
        return (True, assignment) if ok else (None, None)

    if all(len(clause) <= 2 for clause in clauses):
        log("Residual formula is 2-SAT")
        stats["stage"] = "2-SAT"
        sat2, assignment = _solve_two_sat(clauses)
        if not sat2:
            stats["comments"].append("c decided by: 2-SAT (implication graph)")
            return False, None
        ok, checked = check(formula, solution, set(assignment))
        if ok:
            stats["comments"].append("c decided by: 2-SAT (implication graph)")
        return (True, checked) if ok else (None, None)

    graph, num_variables, bound = reduction.reduce_sat_to_mids(clauses, max_variable)
    log(f"MIDS instance: {graph.number_of_nodes()} vertices, {graph.number_of_edges()} edges, "
        f"{num_variables} variables, {bound} copies of each clause vertex")
    stats.update(mids_vertices=graph.number_of_nodes(), mids_edges=graph.number_of_edges(),
                 mids_target=num_variables, mids_bound=bound)
    started = time.time()
    independent_dominating_set = find_independent_dominating_set(graph)
    size = len(independent_dominating_set)
    stats.update(siriaisa_seconds=time.time() - started, mids_size=size)
    log(f"Siriaisa independent dominating set: {size} vertices (N = {num_variables}, bound = {bound})")

    if size < bound:
        certificate = reduction.decode_mids(independent_dominating_set, max_variable)
        certificate -= {-x for x in list(certificate)}
        ok, full = check(formula, solution, certificate)
        if ok:
            log("MIDS: decoded assignment verified")
            stats["stage"] = "mids"
            stats["comments"].append(f"c decided by: MIDS graph (Siriaisa's set has {size} vertices, N = {num_variables})")
            return True, full
        log("MIDS: the decoded assignment does not satisfy the formula")
        stats["stage"] = "mids (undecided)"
        stats["comments"].append(f"c MIDS graph: {graph.number_of_nodes()} vertices; Siriaisa's set: {size} vertices; "
                                 f"the decoded assignment does not satisfy the formula")
        return None, None

    # Conjecture: Siriaisa's approximation ratio is at most 2 * sqrt(n); |S| > 2 * sqrt(n) * N <=> |S|^2 > 4 * N^2 * n.
    n = graph.number_of_nodes()
    if size * size > 4 * num_variables ** 2 * n:
        log("MIDS: Siriaisa's set exceeds 2 * sqrt(n) * N")
        stats["stage"] = "mids (conjecture)"
        stats["comments"].append(f"c decided by: MIDS graph under the 2*sqrt(n) conjecture (Siriaisa's set has {size} "
                                 f"vertices > 2*sqrt(n)*N, n = {n}, N = {num_variables})")
        return False, None
    stats["stage"] = "mids (undecided)"
    stats["comments"].append(f"c MIDS graph: {n} vertices; Siriaisa's set: {size} vertices, "
                             f"not above 2*sqrt(n)*N (N = {num_variables})")
    return None, None

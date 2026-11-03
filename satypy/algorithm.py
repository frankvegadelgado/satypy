import time

from siriaisa.algorithm import find_independent_dominating_set

from . import reduction, utils

#: Largest number of nested branchings on a clause named by Siriaisa's set (each multiplies the work by the clause width).
DEFAULT_BRANCH_DEPTH = 2

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

def solve(formula, logger=None, stats=None, branch_depth=DEFAULT_BRANCH_DEPTH):
    """Decide a CNF formula; see _solve. This wrapper is the final certification gate: a
    SATISFIABLE answer is returned only if the assignment is consistent (no variable with both
    signs) and contains a literal of every clause of the original formula; otherwise the
    answer is downgraded to UNKNOWN."""
    stats = {} if stats is None else stats
    stats["comments"] = []
    satisfiability, answer = _solve(formula, logger, stats, branch_depth)
    if satisfiability is True:
        if answer is None:
            return None, None
        literals = set(answer)
        if any(-lit in literals for lit in literals) or not utils.satisfies(formula, literals):
            if logger is not None:
                utils.println("Certification failed: the assignment is rejected", logger)
            return None, None
    return satisfiability, answer


def _solve(formula, logger=None, stats=None, branch_depth=DEFAULT_BRANCH_DEPTH):
    """Decide a CNF formula given as a list of clauses (lists of non-zero integers; variable IDs
    need not be 1..n, contiguous or sorted).

    1. reduce_sat_to_simplified_sat: unit propagation and pure literals (UNSAT on conflicts);
    2. residual 2-SAT: solved exactly by _solve_two_sat;
    3. otherwise reduce_sat_to_mids (the residual formula with N variables and m clauses -> a graph
       with n vertices: an edge {v, -v} per variable and bound copies of a vertex per clause, adjacent
       to its literals, with bound + N > 2N * N) and Siriaisa's independent dominating set S:
       - |S| < bound: S has no clause vertex, so it is one endpoint of each edge {v, -v} and it is
         decoded into an assignment, which is verified (SATISFIABLE);
       - |S| > 2N * N (always the case when |S| >= bound): S holds the copies of the clauses of a
         set F, with |F| = floor(|S| / bound), and its literals, completed with False, falsify at most |F|
         clauses. If branch_depth > 0, the formula is split on a shortest falsified clause C (the formula
         implies C, so it is satisfiable iff some formula + [l], l in C, is) and each branch is decided by
         _solve with branch_depth - 1: SATISFIABLE if a branch is, UNSATISFIABLE if every branch is.
         Without branching (depth 0), or if a branch is UNKNOWN, UNSATISFIABLE by the ratio rule: on a
         satisfiable formula Siriaisa's set has N vertices or a ratio larger than 2N, so the rule assumes
         that its ratio on the graph is at most 2N (a satisfiable formula has a MIDS of N vertices, an
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

    # Ratio rule: on a satisfiable formula Siriaisa's set has N vertices or more than 2N * N (ratio larger than 2N).
    n = graph.number_of_nodes()
    if size > 2 * num_variables * num_variables:
        if branch_depth > 0:
            decided = _branch(formula, clauses, solution, independent_dominating_set, max_variable, bound,
                              logger, stats, branch_depth)
            if decided is not None:
                return decided
        log("MIDS: Siriaisa's set exceeds 2N * N")
        stats["stage"] = "mids (ratio rule)"
        stats["comments"].append(f"c decided by: MIDS graph under the ratio-2N rule (Siriaisa's set has {size} "
                                 f"vertices > 2N*N, n = {n}, N = {num_variables})")
        return False, None
    stats["stage"] = "mids (undecided)"
    stats["comments"].append(f"c MIDS graph: {n} vertices; Siriaisa's set: {size} vertices, "
                             f"not above 2N*N (N = {num_variables})")
    return None, None


def _branch(formula, clauses, solution, independent_dominating_set, max_variable, bound, logger, stats, branch_depth):
    """Exact split of the residual formula `clauses` on a clause named by Siriaisa's set S.

    S holds the copies of the clauses of a set F with |F| = floor(|S| / bound), and its literals, completed with
    False on the other variables, falsify at most |F| clauses. The formula implies each of its clauses C, so it is
    satisfiable iff clauses + [[l]] is for some literal l of C; every branch is decided by _solve with
    branch_depth - 1. Returns (True, assignment) if a branch is satisfiable and its assignment, with the committed
    literals `solution`, satisfies `formula`; (False, None) if every branch is unsatisfiable; None otherwise (the
    caller then keeps its own decision)."""
    literals = reduction.decode_mids(independent_dominating_set, max_variable)
    variables = {abs(lit) for clause in clauses for lit in clause}
    completed = literals | {-v for v in variables if v not in literals and -v not in literals}
    falsified = [clause for clause in clauses if not any(lit in completed for lit in clause)]
    copies = len(independent_dominating_set) // bound
    if not falsified:
        ok, full = check(formula, solution, completed)
        if ok:
            stats["stage"] = "mids (decoded)"
            stats["comments"].append(f"c decided by: MIDS graph (Siriaisa's set holds the copies of {copies} "
                                     f"clause(s); its literals satisfy the formula)")
            return True, full
        return None
    clause = min(falsified, key=len)
    if logger is not None:
        utils.println(f"MIDS: Siriaisa's set holds the copies of {copies} clause(s); its literals falsify "
                      f"{len(falsified)}; branching on {sorted(clause, key=abs)}", logger)
    undecided = False
    for lit in sorted(clause, key=abs):
        branch_stats = {}
        satisfiability, answer = _solve(clauses + [[lit]], logger, branch_stats, branch_depth - 1)
        if satisfiability is True:
            ok, full = check(formula, solution, set(answer))
            if ok:
                stats["stage"] = "mids (branching)"
                stats["comments"].append(f"c decided by: branching on the clause {sorted(clause, key=abs)} named by "
                                         f"Siriaisa's set (branch {lit}: {branch_stats.get('stage', '')})")
                return True, full
            undecided = True
        elif satisfiability is None:
            undecided = True
    if undecided:
        return None
    stats["stage"] = "mids (branching)"
    stats["comments"].append(f"c decided by: branching on the clause {sorted(clause, key=abs)} named by Siriaisa's "
                             f"set (every branch unsatisfiable)")
    return False, None

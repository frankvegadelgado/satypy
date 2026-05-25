from . import reduction
from . import solver

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

def solve(formula):
    # empty formula
    if not formula:
        return True, frozenset()

    variables = {abs(lit) for clause in formula for lit in clause}
    max_variable = max(variables)

    # simplification
    clauses, solution = reduction.reduce_sat_to_simplified_sat(formula)
    if clauses is None:
        return False, None
    if not clauses:
        ok, assignment = check(formula, solution, set())
        if ok:
            return True, assignment
        # should not happen, but fallback
        return False, None

    # 2-SAT residual
    if all(len(clause) <= 2 for clause in clauses):
        sat2, assignment = _solve_two_sat(clauses)
        if not sat2:
            return False, None
        ok, checked = check(formula, solution, set(assignment))
        if ok:
            return True, checked
        # fallback
        return False, None

    sets, k, W, bound = reduction.reduce_sat_to_exact_subset_sum(clauses, max_variable)
    for certificate in solver.first_solution(sets, k, W, bound):
        # first_solution reconstructs the reduction's mandatory-choice
        # groups (one of {v, -v} per variable, two of three per clause
        # triangle) and walks them with no backtracking, so every
        # certificate it yields already decodes to a consistent partial
        # assignment -- no conflicting-literal cleanup needed here.
        assignment = {v for v, _ in certificate if abs(v) <= max_variable}
        ok, full = check(formula, solution, assignment)
        if ok:
            return True, full
    return False, None
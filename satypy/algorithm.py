import time

import networkx as nx

from .coloured import colour_forced_independent_dominating_set
from furones.algorithm import find_dominating_set

from . import reduction, utils


#: Assumption of the last stage: when the independent dominating set forced by the colour classes of the variable cycles
#: (the set of smallest size that the descent finds) holds a clause vertex, the formula is declared unsatisfiable (the
#: set holds a clause vertex only if the descent found no assignment that satisfies every clause). With False the
#: answer there is UNKNOWN, so that UNSATISFIABLE is printed only when it is proved. With True (the default) the
#: UNSATISFIABLE of that stage is an assumption, not a proof: the descent may miss an assignment (the comment line
#: "c decided by" and the stage "mds (assumption)" say so).
ASSUME_COLOUR_OPTIMAL = True

#: Starting points of the colour-forced set, tried in this order; the set with fewest clause vertices is kept and the
#: search stops at a set without clause vertices. "none": every cycle starts with its first colour class;
#: "furones": the dominating set of the MDS graph computed by Furones (the package furones; independence is only needed
#: inside the cycles, and the colour classes provide it). A start gives each cycle the colour class that holds more of
#: its vertices.
STARTS = ("none", "furones")

#: True: the dominating set of Furones is improved (furones.improve: union re-prune, weighted swap search,
#: consensus forcing, final refinement) on the formula given to solve(), not on its branches.
IMPROVE_START = True


def _start_set(graph, name, improve):
    """The start named `name` of STARTS as a set of vertices of `graph` (None for "none")."""
    if name == "furones":
        index = nx.convert_node_labels_to_integers(graph, label_attribute="vertex")
        found = find_dominating_set(index, improve=improve)
        return {index.nodes[i]["vertex"] for i in found}
    return None


def default_branch_depth(formula):
    """Depth of the branching on a clause falsified by the colour-forced set: max(2, floor(log_3(m + n))) for a formula with m
    clauses and n variables. Each level multiplies the work by the clause width, so for clauses of width 3 the branching solves
    (3^(d + 1) - 1) / 2 formulas, at most max(13, 3 * (m + n) / 2)."""
    size = len(formula) + len({abs(lit) for clause in formula for lit in clause})
    depth = 2
    while 3 ** (depth + 1) <= size:
        depth += 1
    return depth

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

def solve(formula, logger=None, stats=None, branch_depth=None):
    """Decide a CNF formula; see _solve. This wrapper is the final certification gate: a
    SATISFIABLE answer is returned only if the assignment is consistent (no variable with both
    signs) and contains a literal of every clause of the original formula; otherwise the
    answer is downgraded to UNKNOWN."""
    stats = {} if stats is None else stats
    stats["comments"] = []
    if branch_depth is None:
        branch_depth = default_branch_depth(formula)
    stats["branch_depth"] = branch_depth
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


def _solve(formula, logger, stats, branch_depth):
    """Decide a CNF formula given as a list of clauses (lists of non-zero integers; variable IDs
    need not be 1..n, contiguous or sorted).

    1. reduce_sat_to_simplified_sat: unit propagation and pure literals (UNSAT on conflicts);
    2. residual 2-SAT: solved exactly by _solve_two_sat;
    3. otherwise reduce_sat_to_monotone_3sat (the residual formula -> an equisatisfiable monotone formula with N
       variables and L occurrence pairs) and reduce_monotone_3sat_to_mds with one vertex per clause (a bipartite
       graph of maximum degree 3 in which the occurrences of each variable form an even cycle whose edges are the
       independence edges and the links). The colour-forced set F (coloured) starts from each of STARTS
       (the first colour class of every cycle, the dominating set of Furones improved by furones.improve)
       and the one with fewest clause vertices is kept: from each cycle F takes one of its two colour classes, that is, all the vertices
       (v, i) or all the vertices (-v, i), and the clause vertices that no chosen vertex dominates; the choices are
       improved by flipping a cycle while that makes F smaller and by a tabu search over the flips. F has L vertices plus one per clause not satisfied by
       the assignment it defines, so F is consistent:
       - no clause vertex in F: the literals of its vertices are an assignment, which is verified (SATISFIABLE); if it
         does not satisfy the formula the answer is UNKNOWN;
       - otherwise, if branch_depth > 0, the formula is split on a shortest clause C falsified by those literals
         completed with False (the formula implies C, so it is satisfiable iff some formula + [l], l in C, is) and
         each branch is decided by _solve with branch_depth - 1: SATISFIABLE if a branch is, UNSATISFIABLE if every
         branch is. Without branching (depth 0), or if a branch is UNKNOWN: UNSATISFIABLE if ASSUME_COLOUR_OPTIMAL
         (the assumption that F is a minimum independent dominating set among the colour-forced sets), UNKNOWN
         otherwise.
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

    monotone, info = reduction.reduce_sat_to_monotone_3sat(clauses, max_variable)
    graph, num_variables, occurrences, _ = reduction.reduce_monotone_3sat_to_mds(monotone, copies=1)
    degree = max(d for _, d in graph.degree)
    log(f"MDS instance: {graph.number_of_nodes()} vertices, {graph.number_of_edges()} edges, maximum degree {degree}, "
        f"{num_variables} variables and {occurrences} occurrence pairs of the monotone formula")
    stats.update(mds_vertices=graph.number_of_nodes(), mds_edges=graph.number_of_edges(), mds_max_degree=degree,
                 mds_target=occurrences)
    started = time.time()
    groups = list(reduction.mds_variable_groups(graph).values())
    forced, unsatisfied, best_start = None, None, ""
    for name in STARTS:
        candidate = colour_forced_independent_dominating_set(graph, groups, _start_set(graph, name, IMPROVE_START and "branch_depth" in stats))
        count = sum(1 for vertex in candidate if vertex[0] == "clause")
        log(f"Start {name}: colour-forced set with {len(candidate)} vertices, {count} clause vertices")
        if unsatisfied is None or count < unsatisfied:
            forced, unsatisfied, best_start = candidate, count, name
        if unsatisfied == 0:
            break
    size = len(forced)
    stats.update(mds_seconds=time.time() - started, mds_size=size, mds_start=best_start,
                 mds_unsatisfied=unsatisfied)
    log(f"Colour-forced set: {size} vertices, {unsatisfied} clause vertices (L = {occurrences}, start {best_start})")

    literals = reduction.decode_mds(forced, max_variable)
    if unsatisfied == 0:
        ok, full = check(formula, solution, literals)
        if ok:
            log("MDS: decoded assignment verified")
            stats["stage"] = "mds"
            stats["comments"].append(f"c decided by: MDS graph (colour-forced set of L = {occurrences} vertices)")
            return True, full
        log("MDS: the decoded assignment does not satisfy the formula")
        stats["stage"] = "mds (undecided)"
        stats["comments"].append(f"c MDS graph: {graph.number_of_nodes()} vertices; the decoded assignment does "
                                 f"not satisfy the formula")
        return None, None

    if branch_depth > 0:
        decided = _branch(formula, clauses, solution, literals, unsatisfied, logger, stats, branch_depth)
        if decided is not None:
            return decided
    if ASSUME_COLOUR_OPTIMAL:
        log("MDS: the colour-forced set holds clause vertices")
        stats["stage"] = "mds (assumption)"
        stats["comments"].append(f"c decided by: MDS graph under the assumption that the colour-forced set is "
                                 f"minimum (it has {unsatisfied} clause vertices, L = {occurrences})")
        return False, None
    stats["stage"] = "mds (undecided)"
    stats["comments"].append(f"c MDS graph: the colour-forced set holds {unsatisfied} clause vertices")
    return None, None


def _branch(formula, clauses, solution, literals, unsatisfied, logger, stats, branch_depth):
    """Exact split of the residual formula `clauses` on a clause falsified by `literals`.

    `literals` (the literals of the colour-forced set, completed with False on the other variables) falsify some
    clauses. The formula implies each of its clauses C, so it is satisfiable iff clauses + [[l]] is for some literal l
    of C; every branch is decided by _solve with branch_depth - 1. Returns (True, assignment) if a branch is
    satisfiable and its assignment, with the committed literals `solution`, satisfies `formula`; (False, None) if every
    branch is unsatisfiable; None otherwise (the caller then keeps its own decision)."""
    variables = {abs(lit) for clause in clauses for lit in clause}
    completed = literals | {-v for v in variables if v not in literals and -v not in literals}
    falsified = [clause for clause in clauses if not any(lit in completed for lit in clause)]
    if not falsified:
        ok, full = check(formula, solution, completed)
        if ok:
            stats["stage"] = "mds (decoded)"
            stats["comments"].append("c decided by: MDS graph (the literals of the colour-forced set satisfy the "
                                     "formula)")
            return True, full
        return None
    clause = min(falsified, key=len)
    if logger is not None:
        utils.println(f"MDS: the colour-forced set holds {unsatisfied} clause vertices; its literals falsify "
                      f"{len(falsified)}; branching on {sorted(clause, key=abs)}", logger)
    undecided = False
    for lit in sorted(clause, key=abs):
        branch_stats = {}
        satisfiability, answer = _solve(clauses + [[lit]], logger, branch_stats, branch_depth - 1)
        if satisfiability is True:
            ok, full = check(formula, solution, set(answer))
            if ok:
                stats["stage"] = "mds (branching)"
                stats["comments"].append(f"c decided by: branching on the clause {sorted(clause, key=abs)} falsified "
                                         f"by the colour-forced set (branch {lit}: {branch_stats.get('stage', '')})")
                return True, full
            undecided = True
        elif satisfiability is None:
            undecided = True
    if undecided:
        return None
    stats["stage"] = "mds (branching)"
    stats["comments"].append(f"c decided by: branching on the clause {sorted(clause, key=abs)} falsified by the "
                             f"colour-forced set (every branch unsatisfiable)")
    return False, None

# Colour-forced independent dominating sets of bipartite graphs.
# Author: Frank Vega

"""
Colour-forced independent dominating sets of a bipartite graph.

Let ``G`` be a bipartite graph and ``groups`` a list of vertex sets, each connected, with no edge between two different
groups, such that each of the two colour classes of a group (the bipartition of ``G`` restricted to the group)
dominates the group; this holds for an even cycle and for a single edge. The vertices outside the groups (the *free*
vertices) are pairwise non-adjacent.

A *colour-forced* set takes, from each group, exactly one of its two colour classes, and adds every free vertex that no
chosen vertex dominates. It is an independent dominating set: a colour class is independent, groups are not adjacent,
the added free vertices have no chosen neighbour and are not adjacent to each other, and every other vertex is dominated.
If the two colour classes of every group have the same size, the size of the set is ``sum of the class sizes`` plus the
number of undominated free vertices: the choices of the colour classes decide the size.

:func:`colour_forced_ids` starts from the colour classes that hold most of a given set (``start``) and flips a group
to its other colour class whenever that makes the set smaller, until no flip does (at most ``max_passes`` passes);
each pass takes ``O(n + m)`` time. Then a tabu search runs, ``steps_per_group`` steps per group: it picks a free vertex
that no chosen vertex dominates (an unsatisfied clause) and flips one of the groups adjacent to it, the one with the
smallest increase in size (with probability ``NOISE`` a random one), forbidding the flipped group for ``TENURE`` steps;
the smallest set found is kept. In a graph of maximum degree 3 a vertex has at most 3 neighbours, so a step takes
constant time apart from the size of the flipped group (the number of its vertices, the occurrences of a variable).
"""

from __future__ import annotations

from typing import Any, Hashable, List, Optional, Sequence, Set, Tuple

from collections import deque
import random

import networkx as nx


def two_colouring(adj: List[List[int]]) -> Tuple[List[int], List[bool]]:
    """Breadth-first 2-colouring of the index graph ``adj``. Returns ``(colour, bipartite)``: ``colour[v]`` in {0, 1}
    and ``bipartite[c]`` True when component ``c`` (components numbered in order of their smallest vertex) has no
    edge inside a colour class, so that its colouring is its bipartition. ``O(n + m)``."""
    n = len(adj)
    colour = [-1] * n
    bipartite: List[bool] = []
    for s in range(n):
        if colour[s] != -1:
            continue
        colour[s] = 0
        ok = True
        queue = deque([s])
        while queue:
            x = queue.popleft()
            for y in adj[x]:
                if colour[y] == -1:
                    colour[y] = 1 - colour[x]
                    queue.append(y)
                elif colour[y] == colour[x]:
                    ok = False
        bipartite.append(ok)
    return colour, bipartite


def _complete(adj: List[List[int]], seed: Sequence[int]) -> List[bool]:
    """Membership list of the independent set ``seed`` completed into a maximal independent set (an independent
    dominating set) by adding, in index order, the vertices that no vertex of the set dominates. ``O(n + m)``."""
    n = len(adj)
    in_s = [False] * n
    dominated = [False] * n
    for v in seed:
        in_s[v] = True
        dominated[v] = True
        for y in adj[v]:
            dominated[y] = True
    for v in range(n):
        if not dominated[v]:
            in_s[v] = True
            dominated[v] = True
            for y in adj[v]:
                dominated[y] = True
    return in_s


#: Largest number of passes over the groups.
DEFAULT_PASSES: int = 50

#: Steps of the tabu search per group (0: none), noise probability and tabu tenure of the tabu search.
DEFAULT_STEPS_PER_GROUP: int = 50
NOISE: float = 0.2
TENURE: int = 10
SEED: int = 2026


def colour_forced_ids(adj: List[List[int]], groups: Sequence[Sequence[int]], start: Optional[Sequence[bool]] = None,
                      max_passes: int = DEFAULT_PASSES, steps_per_group: int = DEFAULT_STEPS_PER_GROUP) -> Tuple[List[bool], List[int]]:
    """Colour-forced independent dominating set of the index graph ``adj`` (see the module docstring).

    ``start`` is a membership list; the colour class of a group with more members of ``start`` is the initial
    choice (colour 0 on ties and without ``start``). Returns ``(in_s, choice)``: the membership list of the set and
    the chosen colour of every group. Raises ``ValueError`` if the graph is not bipartite or the groups do not satisfy
    the conditions above."""
    n = len(adj)
    colour, bipartite = two_colouring(adj)
    if not all(bipartite):
        raise ValueError("the graph is not bipartite")
    group_of = [-1] * n
    for g, members in enumerate(groups):
        for v in members:
            group_of[v] = g
    classes: List[List[List[int]]] = []
    for g, members in enumerate(groups):
        by_colour = [[v for v in members if colour[v] == 0], [v for v in members if colour[v] == 1]]
        for c in (0, 1):
            chosen = set(by_colour[c])
            for v in members:
                if v not in chosen and not any(y in chosen for y in adj[v]):
                    raise ValueError("a colour class of a group does not dominate the group")
        for v in members:
            if any(group_of[y] not in (-1, g) for y in adj[v]):
                raise ValueError("two groups are adjacent")
        classes.append(by_colour)
    free = [v for v in range(n) if group_of[v] == -1]
    for v in free:
        if any(group_of[y] == -1 for y in adj[v]):
            raise ValueError("two free vertices are adjacent")

    free_adj = [[y for y in adj[v] if group_of[y] == -1] for v in range(n)]
    choice = [0] * len(groups)
    if start is not None:
        for g in range(len(groups)):
            choice[g] = 1 if sum(1 for v in classes[g][1] if start[v]) > sum(1 for v in classes[g][0] if start[v]) else 0

    def counts(selection):
        count = [0] * n   # chosen neighbours of each free vertex
        for g in range(len(groups)):
            for v in classes[g][selection[g]]:
                for y in free_adj[v]:
                    count[y] += 1
        return count

    count = counts(choice)

    for _ in range(max_passes):
        improved = False
        for g in range(len(groups)):
            old, new = classes[g][choice[g]], classes[g][1 - choice[g]]
            delta = len(new) - len(old)
            for v in old:
                for y in free_adj[v]:
                    count[y] -= 1
                    if count[y] == 0:
                        delta += 1
            for v in new:
                for y in free_adj[v]:
                    if count[y] == 0:
                        delta -= 1
                    count[y] += 1
            if delta < 0:
                choice[g] = 1 - choice[g]
                improved = True
            else:   # undo
                for v in new:
                    for y in free_adj[v]:
                        count[y] -= 1
                for v in old:
                    for y in free_adj[v]:
                        count[y] += 1
        if not improved:
            break

    if steps_per_group > 0 and groups:
        choice = _tabu_search(adj, free_adj, group_of, classes, choice, count, steps_per_group)
        count = counts(choice)

    seed = [v for g in range(len(groups)) for v in classes[g][choice[g]]]
    seed.extend(v for v in free if count[v] == 0)
    return _complete(adj, seed), choice


def _tabu_search(adj, free_adj, group_of, classes, choice, count, steps_per_group):
    """Tabu search over the choices of the groups (see the module docstring); returns the best choice found."""
    rng = random.Random(SEED)
    groups = len(classes)
    choice = choice[:]
    count = count[:]
    unsatisfied = [v for v in range(len(adj)) if group_of[v] == -1 and count[v] == 0]
    position = {v: i for i, v in enumerate(unsatisfied)}

    def add(v):
        position[v] = len(unsatisfied)
        unsatisfied.append(v)

    def remove(v):
        i = position.pop(v)
        last = unsatisfied.pop()
        if last != v:
            unsatisfied[i] = last
            position[last] = i

    total = sum(len(classes[g][choice[g]]) for g in range(groups))
    best = total + len(unsatisfied)
    best_choice = choice[:]
    tabu = [-1] * groups
    tenure = min(TENURE, max(1, groups // 2))

    def score(g):
        old, new = classes[g][choice[g]], classes[g][1 - choice[g]]
        broken = sum(1 for v in old for y in free_adj[v] if count[y] == 1)
        made = sum(1 for v in new for y in free_adj[v] if count[y] == 0)
        return len(new) - len(old) + broken - made

    for step in range(steps_per_group * groups):
        if not unsatisfied:
            break
        r = unsatisfied[rng.randrange(len(unsatisfied))]
        candidates = sorted({group_of[y] for y in adj[r] if group_of[y] != -1})
        if not candidates:
            continue
        allowed = [g for g in candidates if tabu[g] < step] or candidates
        g = rng.choice(allowed) if rng.random() < NOISE else min(allowed, key=score)
        old, new = classes[g][choice[g]], classes[g][1 - choice[g]]
        for v in old:
            for y in free_adj[v]:
                count[y] -= 1
                if count[y] == 0:
                    add(y)
        for v in new:
            for y in free_adj[v]:
                if count[y] == 0:
                    remove(y)
                count[y] += 1
        total += len(new) - len(old)
        choice[g] = 1 - choice[g]
        tabu[g] = step + tenure
        if total + len(unsatisfied) < best:
            best = total + len(unsatisfied)
            best_choice = choice[:]
    return best_choice


def colour_forced_independent_dominating_set(graph: nx.Graph, groups: Sequence[Sequence[Hashable]],
                                             start: Optional[Set[Any]] = None) -> Set[Any]:
    """:func:`colour_forced_ids` on a NetworkX graph: ``groups`` are lists of vertices and ``start`` a set of vertices.
    Returns the set of vertices."""
    nodes = list(graph.nodes())
    index = {v: i for i, v in enumerate(nodes)}
    adj = [[index[u] for u in graph.adj[v]] for v in nodes]
    membership = None if start is None else [v in start for v in nodes]
    in_s, _ = colour_forced_ids(adj, [[index[v] for v in group] for group in groups], membership)
    return {nodes[i] for i, flag in enumerate(in_s) if flag}

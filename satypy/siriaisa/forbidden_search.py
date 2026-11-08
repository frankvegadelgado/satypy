# Version: v0.0.8
# Created on 08/11/2026
# Author: Frank Vega

"""
Independent dominating set that avoids a set of forbidden vertices (Siriaisa 0.0.8).

Given a graph and a set ``F`` of forbidden vertices, the search looks for a set ``S`` of vertices such that

* ``S`` is independent (no two vertices of ``S`` are adjacent),
* ``S`` holds no vertex of ``F``,
* ``S`` is dominating (every vertex is in ``S`` or has a neighbour in ``S``).

Such a set may not exist, and finding it is NP-hard (for the graph of a CNF formula -- a vertex for every literal and
for every clause, the edge ``(x, -x)`` for every variable and each clause joined to its literals -- with the clause
vertices forbidden, the sets are exactly the satisfying assignments). The routine is a weighted local search; it
returns the independent set avoiding ``F`` with fewest undominated vertices that it met, and that set is dominating
exactly when the number of undominated vertices reported is zero.

The search keeps an independent set ``S`` without forbidden vertices and minimises

    cost(S) = sum of w[v] over the undominated vertices v.

A step picks a random undominated vertex ``v`` and inserts the vertex ``z`` of its closed neighbourhood (``z`` not
forbidden) that decreases the cost most -- the weight of the undominated vertices of ``N[z]`` minus the weight of the
vertices that the eviction of the neighbours of ``z`` in ``S`` leaves undominated -- ties broken by age; with
probability :data:`NOISE` a random candidate is taken instead. After every step the weight of every undominated vertex
grows by one, so that violations that persist become more important; the weights are halved when their mean exceeds
:data:`WEIGHT_LIMIT`. Every adjacency scan is charged to a work counter and the search stops at
``max(budget * (n + m), floor)`` units, so for fixed ``budget`` and ``floor`` it runs in ``O(n + m)`` time.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence

from .weighted_search import _IndexedSet

#: Work budget in units of (n + m), and the constant floor of the work.
DEFAULT_BUDGET: float = 50.0
DEFAULT_FLOOR: int = 400_000
DEFAULT_SEED: int = 20261108
#: Probability of a random candidate instead of the best one.
NOISE: float = 0.02
#: Weights are halved when their mean exceeds this value.
WEIGHT_LIMIT: float = 50.0


def forbidden_search(adj: List[List[int]], blocked: Sequence[bool], budget: float = DEFAULT_BUDGET,
                     seed: int = DEFAULT_SEED, floor: int = DEFAULT_FLOOR,
                     info: Optional[Dict] = None) -> List[bool]:
    """The membership list of an independent set of the index graph ``adj`` without vertices ``v`` with
    ``blocked[v]`` true, that leaves fewest vertices undominated among those met by the search (zero if it finds an
    independent dominating set). ``info`` (optional dict) receives ``undominated``, ``steps`` and ``work``."""
    n = len(adj)
    rng = random.Random(seed)
    m = sum(len(a) for a in adj) // 2
    limit = max(budget * (n + m), floor)
    work = n + 2 * m

    # --- start: a random maximal independent set among the allowed vertices ---
    order = [v for v in range(n) if not blocked[v]]
    rng.shuffle(order)
    in_s = [False] * n
    dom = [0] * n                      # |N[v] & S|
    for v in order:
        if dom[v] == 0:
            in_s[v] = True
            dom[v] += 1
            for y in adj[v]:
                dom[y] += 1
    if any(all(blocked[z] for z in (v, *adj[v])) for v in range(n)):
        # a vertex whose closed neighbourhood is forbidden can never be dominated
        if info is not None:
            info.update(undominated=sum(1 for v in range(n) if all(blocked[z] for z in (v, *adj[v]))
                                        or (not any(in_s[z] for z in (v, *adj[v])))), steps=0, work=work)
        return in_s
    w = [1] * n
    undom = _IndexedSet(n)
    for v in range(n):
        if dom[v] == 0:
            undom.add(v)
    best = list(in_s)
    best_undom = len(undom)
    age = [0] * n
    stamp = [0] * n
    clock = 0
    step = 0
    total_w = n

    while len(undom) and best_undom > 0 and work <= limit:
        step += 1
        v = undom.items[rng.randrange(len(undom))]
        cands = [z for z in (v, *adj[v]) if not blocked[z]]
        work += len(adj[v]) + 1
        if not cands:                  # v can never be dominated: it no longer counts
            undom.discard(v)
            continue
        if rng.random() < NOISE:
            z = cands[rng.randrange(len(cands))]
        else:
            z, z_score = -1, 0
            for c in cands:
                clock += 1
                stamp[c] = clock
                for y in adj[c]:
                    stamp[y] = clock
                score = w[c] if dom[c] == 0 else 0
                evicted = []
                for y in adj[c]:
                    if dom[y] == 0:
                        score += w[y]
                    if in_s[y]:
                        evicted.append(y)
                work += 2 * len(adj[c]) + 2
                if evicted:
                    # vertices outside N[c] whose dominators in S are all evicted become undominated
                    loss: Dict[int, int] = {}
                    for x in evicted:
                        work += len(adj[x]) + 1
                        for y in (x, *adj[x]):
                            if stamp[y] != clock:
                                loss[y] = loss.get(y, 0) + 1
                    for y, k in loss.items():
                        if dom[y] == k:
                            score -= w[y]
                if z == -1 or score > z_score or (score == z_score and age[c] < age[z]):
                    z, z_score = c, score
        # --- insert z, evicting its neighbours in S ---
        for x in [x for x in adj[z] if in_s[x]]:
            in_s[x] = False
            dom[x] -= 1
            if dom[x] == 0:
                undom.add(x)
            for y in adj[x]:
                dom[y] -= 1
                if dom[y] == 0:
                    undom.add(y)
            age[x] = step
            work += len(adj[x]) + 1
        if not in_s[z]:
            in_s[z] = True
            if dom[z] == 0:
                undom.discard(z)
            dom[z] += 1
            for y in adj[z]:
                if dom[y] == 0:
                    undom.discard(y)
                dom[y] += 1
            age[z] = step
            work += len(adj[z]) + 1
        if len(undom) < best_undom:
            best_undom = len(undom)
            best = list(in_s)
            work += n
        # --- weights of the undominated vertices ---
        for y in undom.items:
            w[y] += 1
        total_w += len(undom)
        work += len(undom)
        if total_w > WEIGHT_LIMIT * n:
            total_w = 0
            for y in range(n):
                w[y] = max(1, w[y] // 2)
                total_w += w[y]
            work += n
    if info is not None:
        info.update(undominated=best_undom, work=work, steps=step)
    return best

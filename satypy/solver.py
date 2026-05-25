"""Fast solver for the exact-cardinality subset-sum instances produced by
this package's SAT -> 3SAT -> exactly-1-in-3SAT -> k,s-vertex-cover ->
exact-subset-sum reduction (see reduction.py).

An earlier version of this module was a generic, structure-agnostic
"enumerate every exact-k subset-sum solution" DFS: it treated every item as
independently optional and pruned invalid combinations (a label together
with its negation, a clause triangle's three vertices all at once) live,
during the search. That does not scale: the item-level feasibility table
has no notion of those constraints, so a pruned branch just forces
backtracking, and that backtracking is not bounded by any polynomial-delay
argument -- it was the actual source of the catastrophic slowdown observed
on real benchmark instances.

The reduction's output is not really "n independently optional items" --
it is a small number of *mandatory, exclusive* choices:

  - one choice per variable (or auxiliary variable introduced along the
    way): pick exactly one of {v, -v} -- never both, never neither;
  - one choice per clause triangle: pick exactly two of its three
    vertices, equivalently pick exactly one of the three to exclude.

Modelling the problem at the level of these groups instead of individual
items removes the need for any live pruning or backtracking at all: the
suffix feasibility table is built once over groups (not raw items), and a
single greedy left-to-right pass is guaranteed -- by the same
suffix-feasibility argument as a normal subset-sum DP -- to find a complete,
constraint-respecting solution whenever one exists, in one pass with no
dead ends.
"""

from typing import Hashable, Iterable, Iterator, List, Optional, Tuple

Item = Tuple[Hashable, int]


def _validate(items: List[Item], k: int, W: int) -> None:
    for b, w in items:
        if not isinstance(w, int) or isinstance(w, bool) or w <= 0:
            raise ValueError(f"weight for {b!r} must be a positive integer, got {w!r}")
        hash(b)
    if not isinstance(k, int) or k < 0:
        raise ValueError(f"k must be a nonnegative integer, got {k!r}")
    if not isinstance(W, int) or W < 0:
        raise ValueError(f"W must be a nonnegative integer, got {W!r}")


def _group_sat_items(items: List[Item], bound: int) -> Optional[List[List[List[Item]]]]:
    """Reconstruct the mandatory-choice groups implied by the SAT-via-
    vertex-cover-via-subset-sum reduction (see reduction.py):

      - every label ``v`` with ``abs(v) <= bound`` belongs to a *pair*
        group with its negation ``-v``: exactly one of the two must be
        picked (this is the k,s-vertex-cover edge (v, -v): it has to be
        covered, and by the tight cardinality argument -- any exact-size
        cover has *no* slack -- it is covered by exactly one endpoint,
        never both, never neither);
      - every label ``> bound`` is a clause-triangle vertex; the reduction
        spaces consecutive clauses' triangles apart precisely so that three
        labels ``a, a+1, a+2`` found consecutively (sorted) among the
        ``> bound`` labels always belong to the same triangle. Exactly two
        of the three must be picked (a triangle's cover has no slack
        either, for the same reason).

    Returns a list of groups, each group a list of *options*, each option a
    list of ``(label, weight)`` items that are chosen together atomically.
    Returns ``None`` if ``items`` doesn't match this expected shape (so
    callers can fall back rather than silently mis-answer).
    """
    by_label = {}
    for b, w in items:
        if type(b) is not int or b in by_label:
            return None
        by_label[b] = w

    groups: List[List[List[Item]]] = []

    pair_vars = sorted({abs(b) for b in by_label if abs(b) <= bound})
    for v in pair_vars:
        opts = []
        if v in by_label:
            opts.append([(v, by_label[v])])
        if -v in by_label:
            opts.append([(-v, by_label[-v])])
        if not opts:
            return None
        groups.append(opts)

    triangle_labels = sorted(b for b in by_label if b > bound)
    i, n = 0, len(triangle_labels)
    while i < n:
        a = triangle_labels[i]
        if i + 2 <= n - 1 and triangle_labels[i + 1] == a + 1 and triangle_labels[i + 2] == a + 2:
            b_, c_ = a + 1, a + 2
            wa, wb, wc = by_label[a], by_label[b_], by_label[c_]
            groups.append([
                [(b_, wb), (c_, wc)],   # exclude a
                [(a, wa), (c_, wc)],    # exclude b
                [(a, wa), (b_, wb)],    # exclude c
            ])
            i += 3
        else:
            # Should not happen for a well-formed reduction; don't silently
            # drop the item -- surface it as its own mandatory singleton.
            groups.append([[(a, by_label[a])]])
            i += 1

    return groups


def _group_suffix_table(groups: List[List[List[Item]]], W: int) -> List[int]:
    """table[i] = bitmask over sums reachable by choosing exactly one option
    from each of groups[i:]. O((number of options across all groups) * W)
    bit operations total -- pseudo-polynomial in W, i.e. exponential only
    in the bit-length of W (log W), never in the number of groups.
    """
    n = len(groups)
    mask = (1 << (W + 1)) - 1
    table = [0] * (n + 1)
    table[n] = 1  # empty suffix: only sum 0 reachable
    row = 1
    for i in range(n - 1, -1, -1):
        combined = 0
        for opt in groups[i]:
            w = sum(item[1] for item in opt)
            if w <= W:
                combined |= (row << w) & mask
        row = combined
        table[i] = row
    return table


def first_solution(items: Iterable[Item], k: int, W: int, bound: int) -> Iterator[List[Item]]:
    """Find a certificate for the SAT-via-vertex-cover-via-subset-sum
    reduction: a sub-collection of exactly ``k`` items summing to ``W``
    that additionally respects the reduction's mandatory-choice structure
    (see ``_group_sat_items``).

    This does not treat each item as independently optional. It
    reconstructs the mandatory-choice groups the reduction guarantees and
    walks them greedily, group by group, always picking the first option
    whose weight is consistent with the group-level suffix feasibility
    table. Because every group-level choice the table marks feasible is
    *guaranteed* to have a feasible completion (the same suffix-feasibility
    argument used by a plain subset-sum DP, just one dimension smaller
    since cardinality is fixed by the group shapes rather than tracked
    separately), this never backtracks.

    Complexity: O(n_groups * W) bit operations to build the table -- at
    most roughly ``(n_vars + m) * W`` where n_vars/m are the SAT instance's
    variable/clause counts -- and then O(n_groups) more to read off the
    single certificate. Pseudo-polynomial in W (exponential only in the
    bit-length of W, log W), and never exponential in the number of
    variables or clauses: no search tree, no backtracking, one linear pass.

    Yields at most one certificate (a flat list of ``(label, weight)``
    items). Yields nothing if infeasible, or if ``items`` doesn't match the
    expected group shape -- callers should treat that defensively, not as
    proof of unsatisfiability.

    Raises:
        ValueError: if any weight is not a positive integer, or k < 0, or W < 0.
    """
    items = list(items)
    _validate(items, k, W)

    groups = _group_sat_items(items, bound)
    if groups is None:
        return

    expected_k = sum(1 if len(g) == 2 else 2 if len(g) == 3 else len(g[0]) for g in groups)
    if expected_k != k:
        return

    table = _group_suffix_table(groups, W)
    if not (table[0] >> W) & 1:
        return

    result: List[Item] = []
    s = W
    for i, group in enumerate(groups):
        remaining = table[i + 1]
        for opt in group:
            w = sum(item[1] for item in opt)
            if w <= s and (remaining >> (s - w)) & 1:
                result.extend(opt)
                s -= w
                break
        else:
            # table[0] said the whole path is feasible, so every step
            # along the way must offer a feasible option; this is a
            # defensive guard against a logic error, not expected reality.
            return
    yield result

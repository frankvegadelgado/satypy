# SatyPy: SAT Solver through Minimum Independent Dominating Set

![SatyPy: SAT Solver](docs/satypy.png)

This work builds upon [SatyPy: SAT Solver](https://github.com/frankvegadelgado/satypy).

SatyPy decides Boolean formulas in CNF by reducing them to **Minimum Independent Dominating Set** (MIDS) through a
**monotone 3SAT** formula whose variable occurrences form even cycles. The MIDS graph is bipartite with maximum degree 3.
The colour classes of the cycles give a *colour-forced* independent dominating set, improved by flipping cycles; it can
start from the first colour class of every cycle or from the dominating set of the graph computed by Furones (the
package `furones`, version 0.3.9 or later) and improved by a weighted swap search, as `algorithm.STARTS` says. Every `SATISFIABLE`
comes with a checked assignment. `UNSATISFIABLE` is printed when an exact stage proves it, when every branch is proved
unsatisfiable, or, if `algorithm.ASSUME_COLOUR_OPTIMAL` is True, at the deepest level, under the assumption that the colour-forced set
is minimum; with the assumption off (`ASSUME_COLOUR_OPTIMAL = False`) the answer there is `UNKNOWN` (see
[What Is Proved and What Is Assumed](#what-is-proved-and-what-is-assumed)).

# Boolean Satisfiability (SAT) Problem

**Problem:** Given a Boolean formula in Conjunctive Normal Form (CNF), is there a truth assignment that makes the formula evaluate to true?

**Background:**

The Boolean Satisfiability Problem (SAT) is a fundamental problem in computer science. It is known to be NP-complete, which means that any problem whose solution can be verified in polynomial time can be reduced to SAT. This implies that SAT is likely to be computationally difficult, although there is no proof of this.

**Concepts:**

- **Literal:** A variable or its negation (e.g., $x$ or $\neg x$).
- **Clause:** A disjunction (OR) of one or more literals (e.g., $x \vee \neg y \vee z$).
- **Conjunctive Normal Form (CNF):** A Boolean formula where each clause is connected by conjunction (AND).
- **Truth Assignment:** An assignment of truth values (true or false) to all variables in a formula.
- **Satisfying Truth Assignment:** A truth assignment that makes a formula evaluate to true.
- **Satisfiable Formula:** A formula that has a satisfying truth assignment.

**Example:**

Consider the formula $(x_1 \vee ¬x_3 \vee ¬x_2) \wedge (x_3 \vee x_2 \vee x_4)$, where $\vee$ (OR), $\wedge$ (AND) and $\neg$ (NEGATION) are the logic operations. This formula is in CNF with four variables ($x_1$, $x_2$, $x_3$, and $x_4$) and two clauses. A possible satisfying truth assignment is ($x_1$: False, $x_2$: False, $x_3$: True, and $x_4$: False).

**Input format:**

The input for SAT solvers is typically provided in [DIMACS](https://jix.github.io/varisat/manual/0.2.0/formats/dimacs.html) format (`.cnf` files). A DIMACS file consists of three parts:

1. **Header:** The first line specifies the number of variables (n) and clauses (m) in the formula using the format `p cnf n m`.
2. **Clauses:** Each subsequent line represents a clause, where each literal is represented by a variable's index (positive for the variable, negative for its negation). A zero at the end of the line indicates the end of the clause.

**Example `.cnf` file:**

```
p cnf 4 2
1 -3 -2 0
3 2 4 0
```

This is a `.cnf` file representing a Boolean formula in Conjunctive Normal Form (CNF) for the Boolean Satisfiability Problem (SAT). Let's break down what each line means:

- **Header (p cnf 4 2):**

  - `p cnf` indicates it's a CNF formula in DIMACS format.
  - `4` specifies the number of variables in the formula ($x_1$, $x_2$, $x_3$, and $x_4$ in this case).
  - `2` specifies the number of clauses (disjunctions of literals) in the formula.

- **Clauses (1 -3 -2 0 and 3 2 4 0):**
  - Each line represents a clause.
  - A positive integer represents a variable (e.g., `1` represents variable $x_1$).
  - A negative integer represents the negation of a variable (e.g., `-3` represents $\neg x_3$).
  - `0` at the end of the line indicates the end of the clause.

**Explanation of the clauses:**

- `1 -3 -2 0`: This clause translates to $(x_1 \vee \neg x_3 \vee \neg x_2)$, which means at least one of $x_1$, $\neg x_3$, or $\neg x_2$ must be true for the clause to be true.
- `3 2 4 0`: This clause translates to $(x_3 \vee x_2 \vee x_4)$, which means at least one of $x_3$, $x_2$, or $x_3$ must be true for the clause to be true.

**In essence, the formula represented by this `.cnf` file is asking if there exists an assignment of truth values (true or false) to the variables $x_1$, $x_2$, $x_3$, and $x_4$ that makes both clauses true simultaneously.**

## Installation and Setup

**1. Install Python:**

- Ensure you have Python 3.12 or a later version installed on your system. You can download and install it from the official Python website: https://www.python.org/downloads/

**2. Install SatyPy's Library:**

- Open your terminal or command prompt.
- Use `pip` to install the SatyPy library and its dependencies:

```bash
pip install satypy
```

## Running the SAT Solver with SatyPy

Download the repository (it contains sample formulas):

```bash
git clone https://github.com/frankvegadelgado/satypy.git
cd satypy
```

and run `saty` on a DIMACS file (`.cnf`, also compressed as `.xz`, `.lzma`, `.bz2` or `.bzip2`):

```bash
saty -i benchmarks/test_formulas/formula2.cnf
```

Variable identifiers may be any positive integers: they need not be `1..n`, contiguous, or sorted.

## Output Interpretation

SatyPy prints its answer in the DIMACS output format.

- **Satisfiable, with an assignment:**

  ```
  s SATISFIABLE
  v 1 2 -3 0
  ```

  Positive numbers are variables assigned True, negative numbers variables assigned False, and `0` ends the line. The
  assignment has been checked against every clause of the input.

- **Unsatisfiable:** `s UNSATISFIABLE`, when an exact stage proves it, when every branch on a clause falsified by the
  colour-forced set is unsatisfiable, or, at the deepest level, when the colour-forced set holds a clause vertex and
  `algorithm.ASSUME_COLOUR_OPTIMAL` is True (the default; this answer is an assumption, not a proof).

- **Comment lines:** before the answer, SatyPy prints DIMACS comment lines (`c ...`) that report what the MIDS stage
  found and, when the formula is decided, a line `c decided by: ...` naming the stage that decided it (empty clause,
  simplification, 2-SAT, MIDS graph, branching, or MIDS graph under the assumption).

- **Undecided:** `s UNKNOWN`, preceded by the comment lines. It is printed when the assignment of a colour-forced set
  without clause vertices does not satisfy the formula, or, only with `ASSUME_COLOUR_OPTIMAL = False`, when the colour-forced
  set holds a clause vertex and branching decides nothing.

## Examples

The directory `benchmarks/test_formulas` contains five small formulas; `planted_unique_v6_2.cnf` (6 variables, 16
clauses, a single satisfying assignment) exercises the branching step.

```
saty -i benchmarks/test_formulas/formula2.cnf
saty -i benchmarks/test_formulas/formula3.cnf
saty -i benchmarks/test_formulas/planted_unique_v6_2.cnf -b -l
batch_saty -i benchmarks/test_formulas -a -b -c
```

## Command-Line Options

To view the available command-line options for the `saty` command, use the following command in your terminal or command prompt:

```bash
saty -h
```

This will display the help message, which provides information about the available options and their usage:

```bash
usage: saty [-h] -i INPUTFILE [-a] [-b] [-c] [-v] [-t] [-l] [--version]

Solve the Boolean Satisfiability (SAT) problem using a DIMACS file as input.

options:
  -h, --help            show this help message and exit
  -i INPUTFILE, --inputFile INPUTFILE
                        Input file path
  -a, --approximation   enable comparison with a known SAT solver (MiniSat 2.2 via python-sat)
  -b, --bruteForce      enable comparison with the exponential-time brute-force approach (at most 30 variables)
  -c, --count           only state whether the formula is SATISFIABLE, UNSATISFIABLE or UNKNOWN
  -v, --verbose         Enable verbose output
  -t, --timer           Enable timer output
  -l, --log             Enable file logging
  --version             show program's version number and exit
```

Available Options:

    -h, --help: Displays this help message and exits the program.
    -i INPUTFILE, --inputFile INPUTFILE: Specifies the path to the input file containing the Boolean formula. This option is required.
    -a, --approximation: Also solves the formula with MiniSat 2.2 and reports both answers.
    -b, --bruteForce: Also solves the formula by exhaustive search (skipped above 30 variables).
    -c, --count: Prints only SATISFIABLE, UNSATISFIABLE or UNKNOWN instead of the DIMACS assignment.
    -v, --verbose: Enables verbose output, providing more detailed information about the solver's progress.
    -t, --timer: Enables timer output, displaying the time taken by the solver to find a solution.
    -l, --log: Enables file logging, writing detailed information about the solver's execution to a log file.

With `-a` or `-b` every answer is prefixed by its source and any disagreement is reported, for example:

```
saty -i benchmarks/simple/file.cnf -a -b -c
file.cnf: (MiniSat) SATISFIABLE
file.cnf: (Brute Force) SATISFIABLE
file.cnf: (SatyPy) SATISFIABLE
```

By using these command-line options, you can customize the behavior of the `saty` command to suit your specific needs.

### Batch Execution

Batch execution allows you to solve multiple formulas within a directory simultaneously.

To view available command-line options for the `batch_saty` command, use the following in your terminal or command prompt:

```bash
batch_saty -h
```

This will display the following help information:

```bash
usage: batch_saty [-h] -i INPUTDIRECTORY [-a] [-b] [-c] [-v] [-t] [-l] [--version]

Solve the Boolean Satisfiability (SAT) problem using a directory with DIMACS files as input.

options:
  -h, --help            show this help message and exit
  -i INPUTDIRECTORY, --inputDirectory INPUTDIRECTORY
                        Input directory path
  -a, --approximation   enable comparison with a known SAT solver (MiniSat 2.2 via python-sat)
  -b, --bruteForce      enable comparison with the exponential-time brute-force approach (at most 30 variables)
  -c, --count           only state whether each formula is SATISFIABLE, UNSATISFIABLE or UNKNOWN
  -v, --verbose         Enable verbose output
  -t, --timer           Enable timer output
  -l, --log             Enable file logging
  --version             show program's version number and exit
```

The options have the same meaning as for `saty` and apply to every file of the directory (processed in name order).

### Testing with Random Formulas

The `test_saty` command generates random CNF formulas and compares SatyPy against a brute-force search (`-b`) and
against MiniSat 2.2 through [python-sat](https://pypi.org/project/python-sat/) (`-a`):

```bash
test_saty -h
```

```bash
usage: test_saty [-h] -d DIMENSION [-m CLAUSES] [-k WIDTH] [-n NUM_TESTS] [-g] [-r SEED] [-a] [-b] [-c] [-w] [-v] [-l] [--version]

options:
  -d DIMENSION, --dimension DIMENSION   number of variables of each formula
  -m CLAUSES, --clauses CLAUSES         number of clauses (default: round(4.26 * dimension))
  -k WIDTH, --width WIDTH               literals per clause (default: 3)
  -n NUM_TESTS, --num_tests NUM_TESTS   number of tests to run
  -g, --gaps                            use random non-contiguous variable IDs instead of 1..dimension
  -r SEED, --seed SEED                  random seed
  -a, --approximation                   enable comparison with a known SAT solver (MiniSat 2.2 via python-sat)
  -b, --bruteForce                      enable comparison with the exponential-time brute-force approach
  -c, --count                           only state whether each formula is SATISFIABLE, UNSATISFIABLE or UNKNOWN
  -w, --write                           write each generated formula to a DIMACS file in the current directory
  -v, --verbose                         enable verbose output
  -l, --log                             enable file logging
```

Example:

```
test_saty -d 6 -m 12 -n 8 -g -r 7 -a -b -c
```

## How SatyPy Solves a Formula

Variable IDs may be any positive integers (not necessarily `1..n`, contiguous, or sorted).

1. **Empty clause**: a formula containing the empty clause (a lone `0` in DIMACS) is unsatisfiable.
2. **Simplification** (`reduction.reduce_sat_to_simplified_sat`): unit propagation and pure literals. A conflict proves the
   formula unsatisfiable.
3. **2-SAT**: if every remaining clause has at most two literals, the formula is decided exactly by the
   strongly-connected-components algorithm (`algorithm._solve_two_sat`).
4. **Reduction to monotone 3SAT** (`reduction.reduce_sat_to_monotone_3sat`): the residual formula is written as an
   equisatisfiable formula whose clauses have at most 3 literals, all positive or all negative. A clause of `k`
   literals becomes a path of `c = max(1, k − 2) + e` clauses of width at most 3, with `e` in `0, 1, 2`
   (`reduction.MONOTONE_EXTRA_CLAUSES`), and `c − 1` link variables. Clause `j` of the path has a sign `s_j = ±1` that
   alternates with `j`; a link variable has sign `s_j` in clause `j` and `−s_j` in clause `j + 1`. A literal goes to a
   place of its own sign; if its sign does not fit, its variable `x` gets one complement variable `x'`, shared by all the
   clauses, with the clause `(¬x ∨ ¬x')` or `(x ∨ x')` (each only if it is used). The first sign and `e` are chosen to
   need the fewest new variables.
5. **Reduction to MIDS** (`reduction.reduce_monotone_3sat_to_mids` with one vertex per clause): with `L` the number of
   pairs `(v, i)` (the occurrences) of the monotone formula, for each variable `v` and each clause `i` that contains `v`
   there are the vertices `(v, i)` and `(¬v, i)`, joined by an *independence edge*. With `i_1 < … < i_k` the clauses of
   `v`, an edge joins `(¬v, i_j)` and `(v, i_{j+1})` (indices modulo `k`, none if `k = 1`), so the vertices of `v` form
   the even cycle `(v, i_1) – (¬v, i_1) – (v, i_2) – … – (¬v, i_k) – (v, i_1)`, whose edges are the independence edges
   and the links. Each clause `i` is a vertex adjacent to the vertices `(l, i)` of its literals `l`. The graph is
   bipartite (the vertices `(v, i)` and the negative clauses on one side, the vertices `(¬v, i)` and the positive clauses
   on the other) and its maximum degree is 3: a vertex `(l, i)` has the independence edge, one link and one clause edge,
   and a clause has at most 3 literals.
6. **Colour-forced set** (`satypy.coloured`): the colour-forced set takes from each cycle one of its two colour
   classes, that is, all the vertices `(v, i)` (`v` true) or all the vertices `(¬v, i)` (`v` false), and adds the clause
   vertices that no chosen vertex dominates. Independence is needed only inside the cycles, and the colour classes provide
   it. For each start in `algorithm.STARTS` (default `("none", "furones")`) the set is built and the one with fewest clause
   vertices is kept, stopping at a set with none. The starts are: `"none"`, the first colour class of every cycle;
   `"furones"`, the dominating set of the graph computed by `furones.algorithm.find_dominating_set`,
   with `algorithm.IMPROVE_START` (default True) the candidates of Furones are improved
   (`furones.improve`: union re-prune, weighted swap search, consensus forcing, final refinement) on the formula
   given to `solve`, not on its branches. With a start, the initial choice for a cycle is the colour
   class that holds more vertices of the start set. Then a cycle is flipped to its other colour class whenever that
   makes the set smaller, until no flip does (`coloured.colour_forced_ids`, `O(n + m)` per pass). A tabu search
   follows (`coloured.DEFAULT_STEPS_PER_GROUP` = 50 steps per cycle): it takes a clause vertex that no chosen
   vertex dominates and flips the adjacent cycle that increases the size least (a random one with probability 0.2),
   forbidding the flipped cycle for 10 steps, and keeps the smallest set found. The
   set has `L` vertices plus one per clause that has no true literal under the assignment it defines, and:
   - if it holds no clause vertex, `reduction.decode_mids` reads the literals `l` of its vertices `(l, i)`; the completed
     assignment is verified against the input (`s SATISFIABLE`), and if it does not satisfy the formula the answer is
     `s UNKNOWN`;
   - otherwise step 7 runs.
7. **Branching on a clause falsified by the colour-forced set** (`algorithm._branch`, up to depth
   `d = max(2, ⌊log₃(m + n)⌋)`, `algorithm.default_branch_depth`, with `m` clauses and `n` variables in the input): the
   literals of the set, completed with False, either satisfy the formula (`s SATISFIABLE`) or falsify some clauses.
   SatyPy takes a shortest falsified clause `C` and decides every formula `φ ∧ ℓ`, `ℓ ∈ C`, with steps 2–7 and one level
   less: the formula implies `C`, so it is satisfiable exactly when some branch is.
   - some branch satisfiable: `s SATISFIABLE`, with the checked assignment of that branch;
   - every branch unsatisfiable: `s UNSATISFIABLE`;
   - at depth 0 (no branching left): `s UNSATISFIABLE` if `algorithm.ASSUME_COLOUR_OPTIMAL` is True, `s UNKNOWN`
     otherwise.

`s SATISFIABLE` is printed only after the assignment has been checked to be consistent and to contain a literal of
every clause of the input (a final certification gate in `algorithm.solve`). `s UNSATISFIABLE` comes from steps 1–3, from
the branching, or from the assumption at depth 0. `algorithm.solve(formula, branch_depth=0)` gives the answer without
branching. Use `-l` to see each stage in `app.log`.

## What Is Proved and What Is Assumed

Write `L` for the occurrence pairs `(v, i)` of the monotone formula, `G` for its MIDS graph (one vertex per clause), `n`
for its vertices and `i(G)` for the size of a minimum independent dominating set.

**Proved.**

- *Equisatisfiability of the monotone formula.* Renaming a link variable `w_j` to `¬w_j` in every second link turns the
  path of step 4 into the standard split of a clause, which is satisfiable exactly when some literal is true; a complement
  clause `(¬x ∨ ¬x')` makes `x'` true only if `x` is false, and `(x ∨ x')` makes `x'` false only if `x` is true. So every
  satisfying assignment of the residual formula extends to the monotone formula, and every satisfying assignment of the
  monotone formula, restricted to the variables of the residual formula, satisfies it.
- *The graph.* It is bipartite and its maximum degree is 3. The two colour classes of the cycle of a variable with `k`
  occurrences have `k` vertices each, are independent, and each dominates the cycle.
- *Colour-forced sets.* Choosing one colour class from every cycle and adding the clause vertices that no chosen vertex
  dominates gives an independent dominating set (the colour classes are independent, the cycles are not adjacent to
  each other, and the added clause vertices are not adjacent to the chosen vertices nor to each other). Its size is `L`
  plus the number of clauses with no true literal under the assignment that the choice defines. So a colour-forced
  set of `L` vertices exists exactly when the monotone formula is satisfiable, and the smallest colour-forced set
  corresponds to an assignment that falsifies the fewest clauses.
- *Bounded degree.* In a graph of maximum degree 3 every independent dominating set `S` satisfies `n/4 ≤ |S| ≤ n`, so
  `|S| / i(G) ≤ 4` for every independent dominating set `S`.
- *The answers.* Every `SATISFIABLE` answer carries a checked assignment. `UNSATISFIABLE` comes from the exact stages
  1–3, from branching when every branch is unsatisfiable, or, at depth 0, from the assumption below.
- *Branching.* Splitting on a clause is exact, and branching to depth `d` runs the MIDS stage at most
  `1 + w + … + w^d` times (`w` the largest clause width). With `d = max(2, ⌊log₃(m + n)⌋)` and `w = 3` that is
  `(3^(d+1) − 1)/2 ≤ max(13, 3(m + n)/2)` runs.

**Not proved.**

- *The assumption.* `UNSATISFIABLE` at depth 0 assumes that the colour-forced set found by the flips is a smallest
  colour-forced set. Finding a smallest colour-forced set is finding an assignment that falsifies the fewest clauses
  of the monotone formula, which decides satisfiability.
- A minimum independent dominating set of `G` can be smaller than the colour-forced sets, because a cycle of `2k`
  vertices has independent dominating sets of about `2k/3` vertices besides its two colour classes; the colour-forced set
  restricts the search to the colour classes.

## Running the Experiments

The folder `car/` contains four experiment scripts. All run from the repository root (or from `car/`) with or without
SatyPy installed: they use the repository's own `satypy/`. `networkx` and `furones` (0.3.9 or later) must be installed, and
`python-sat` for the comparison with MiniSat.

**`car/small_formulas.py`** decides every formula with SatyPy and with exhaustive search over all assignments and
compares the answers. Its formulas are the small DIMACS files of `benchmarks/simple` and `benchmarks/test_formulas`
(at most `--max-file-variables` variables) and random k-CNF formulas.

```bash
python car/small_formulas.py
python car/small_formulas.py --variables 3 6 --clauses 16 --repeat 10 --seed 7
python car/small_formulas.py --no-files --width 4
```

| Option | Meaning (default) |
|---|---|
| `--variables MIN MAX` | number of variables of the random formulas (3 5) |
| `--clauses M` | largest number of clauses; every number from 1 to `M` is used (12) |
| `--width K` | literals per clause (3) |
| `--repeat R` | random formulas per number of variables and clauses (5) |
| `--seed S` | random seed (2026) |
| `--max-file-variables V` | largest DIMACS file included (10) |
| `--no-files` | random formulas only |
| `-o FILE` | output CSV (`car/small_formulas_results.csv`) |

For each formula it prints and writes the expected answer, SatyPy's answer, whether it is correct, the deciding stage,
and, for the formulas that reach the MIDS graph, its vertices, edges, maximum degree, the size of the colour-forced set and the number of clause vertices in it. The summary counts correct,
wrong and unknown answers and lists every wrong one.

**`car/medium_formulas.py`** and **`car/large_formulas.py`** compare SatyPy with MiniSat 2.2 (python-sat) on random
k-CNF formulas with `round(ratio · variables)` clauses; MiniSat runs with a conflict budget, and a formula it does not
finish has no reference answer (a `SATISFIABLE` answer of SatyPy is always checked against the formula). 

```bash
python car/medium_formulas.py
python car/medium_formulas.py --variables 30 50 --ratios 4.27 --repeat 20 --seed 7
python car/large_formulas.py
python car/large_formulas.py --variables 100 200 --ratios 4.27 --repeat 3 --reference-conflicts 5000000
```

| Option | Meaning (medium default; large default) |
|---|---|
| `--variables V ...` | numbers of variables (30 50 75; 100 200 400) |
| `--ratios R ...` | clauses per variable (3.0 4.0 4.27 4.5) |
| `--width K` | literals per clause (3) |
| `--repeat R` | random formulas per setting (5; 3) |
| `--seed S` | random seed (2026) |
| `--reference-conflicts C` | conflict budget of MiniSat (1000000; 2000000) |
| `-o FILE` | output CSV (`car/medium_formulas_results.csv`, `car/large_formulas_results.csv`) |

For each formula they print and write MiniSat's answer, SatyPy's answer and its correctness, the deciding stage, the
vertices of the MIDS graph, the size of the colour-forced set, the clause vertices in it and both running times.

**`car/monotone_bipartite.py`** checks the reduction of a CNF formula to monotone 3SAT
(`reduction.reduce_sat_to_monotone_3sat`) and the bipartite occurrence graph of maximum degree 3 built from it
(`reduction.reduce_monotone_3sat_to_bipartite`, with the linear-time maximum cut `reduction.solve_bipartite_max_cut`).
These functions are not used by `algorithm.solve`. On random k-CNF formulas with `k = 2, …, --width` it checks that the
monotone formula has clauses of at most 3 literals, all of one sign; that it is equisatisfiable with the formula
(MiniSat on the monotone formula, exhaustive search on the formula); that a model of the monotone formula restricted
to the original variables satisfies the formula; the new variables (links and complements) against the `k − 3` links
per clause of the standard split; the largest degree of the bipartite graph, the value of the maximum cut, and whether
the literals of the vertices in `S` satisfy the formula.

```bash
python car/monotone_bipartite.py
python car/monotone_bipartite.py --variables 3 7 --clauses 14 --width 6 --repeat 5 --seed 7
```

**Testing a single formula.** Any DIMACS file can be checked against exhaustive search (`-b`, at most 30 variables) and
MiniSat 2.2 (`-a`), with the deciding stage in `app.log` (`-l`):

```bash
saty -i benchmarks/test_formulas/planted_unique_v6_2.cnf -a -b -l
test_saty -d 5 -m 12 -n 20 -r 7 -a -b -c
```

## References

- R. M. Karp, *Reducibility among combinatorial problems*, 1972; M. R. Garey and D. S. Johnson, *Computers and
  Intractability*, Freeman, 1979.
- B. Aspvall, M. F. Plass and R. E. Tarjan, *A linear-time algorithm for testing the truth of certain quantified
  Boolean formulas*, Inform. Process. Lett. 8 (1979) 121–123.
- F. Vega, [Furones 0.3.9](https://pypi.org/project/furones/).
- Y. Cai, K. Su, C. Luo and A. Sattar, *NuMVC: An efficient local search algorithm for minimum vertex cover*, J. Artif. Intell. Res. 46 (2013) 687–716.

## Implementation

- **Programming Language:** Python
- **Author:** Frank Vega

## License

This code is released under the MIT License.

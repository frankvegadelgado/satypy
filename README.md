# SatyPy: SAT Solver through Minimum Independent Dominating Set

![SatyPy: SAT Solver](docs/satypy.png)

This work builds upon [SatyPy: SAT Solver](https://github.com/frankvegadelgado/satypy).

SatyPy decides Boolean formulas in CNF by reducing them to **Minimum Independent Dominating Set** (MIDS) and solving the MIDS instance with
[Siriaisa](https://pypi.org/project/siriaisa/) 0.0.8. Every `SATISFIABLE` comes with a checked assignment, and every
unsatisfiable formula is answered `UNSATISFIABLE` (both are proved, without any conjecture). The only answer that can
be wrong is `UNSATISFIABLE` on a satisfiable formula, and only when Siriaisa's ratio on the MIDS graph exceeds `2N` on
the formula and on every branch that SatyPy explores. The general conjecture behind the method is that Siriaisa has
approximation ratio `n^(1−ε)` with `ε = 1/4`, that is `n^(3/4)` (see
[What Is Proved and What Rests on the Conjecture](#what-is-proved-and-what-rests-on-the-conjecture)).

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

- **Unsatisfiable:** `s UNSATISFIABLE`, when an exact stage proves it, when every branch on the clause named by
  Siriaisa's set is unsatisfiable, or, at the deepest level, when Siriaisa's independent dominating set has more than
  `2N · N` vertices (`N` the number of variables). Every unsatisfiable formula receives this answer; on a satisfiable
  formula it can only appear if Siriaisa's ratio exceeds `2N` on a whole chain of satisfiable branches (see below).

- **Comment lines:** before the answer, SatyPy prints DIMACS comment lines (`c ...`) that report what Siriaisa found
  on the MIDS graph and, when the formula is decided, a line `c decided by: ...` naming the stage that decided it
  (empty clause, simplification, 2-SAT, MIDS graph, branching on the clause named by Siriaisa's set, or MIDS graph
  under the ratio-`2N` rule).

- **Undecided:** `s UNKNOWN`, preceded by the comment lines. It is printed only when a certification check rejects an
  assignment, which the proofs below show cannot happen at the MIDS stage.

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
4. **Reduction to MIDS** (`reduction.reduce_sat_to_mids`): otherwise, with `N` the number of variables of the residual
   formula and `m` its number of clauses, the graph has an edge `{v, −v}` for each variable `v` and, for each clause,
   `bound` vertices adjacent to the literals of the clause (clauses of any width), where
   `bound = 2N² − N + 1` (`reduction.mids_bound`) is the least integer with `bound + N > 2N · N`; the graph has
   `n = 2N + m · bound` vertices. The formula is satisfiable if and only if
   the graph has an independent dominating set of `N` vertices (one endpoint of each edge `{v, −v}`); otherwise every
   independent dominating set contains all `bound` copies of some clause vertex. With the copies of exactly one
   clause it also contains an endpoint of each edge `{v, −v}` (a clause holds at most one of `v`, `−v`), so it has
   `bound + N` vertices; with the copies of two or more clauses it has at least `2 · bound ≥ bound + N` vertices.
   So it has more than `2N · N` vertices: on a satisfiable formula its ratio is larger than `2N`.
5. **Siriaisa** 0.0.8 (`siriaisa.algorithm.find_independent_dominating_set`) computes an independent dominating set `S`:
   - if `|S| < bound`, `S` contains no clause vertex, and `reduction.decode_mids` reads an assignment from it, which is
     verified against the input (`s SATISFIABLE`);
   - otherwise `|S| ≥ bound + N > 2N · N` (an independent dominating set has either `N` or at least `bound + N`
     vertices), and step 6 runs.
6. **Branching on the clause named by Siriaisa's set** (`algorithm._branch`, up to depth
   `algorithm.DEFAULT_BRANCH_DEPTH = 2`): `S` holds the copies of exactly `⌊|S| / bound⌋` clauses, and its literals,
   completed with False, falsify at most that many clauses. If they falsify none, the formula is satisfiable
   (`s SATISFIABLE`). Otherwise SatyPy takes a shortest falsified clause `C` and decides every formula `φ ∧ ℓ`, `ℓ ∈ C`,
   with steps 2–6 and one level less: the formula implies `C`, so it is satisfiable exactly when some branch is.
   - some branch satisfiable: `s SATISFIABLE`, with the checked assignment of that branch;
   - every branch unsatisfiable: `s UNSATISFIABLE`;
   - at depth 0 (no branching left): `s UNSATISFIABLE` by the ratio-`2N` rule, since `|S| > 2N · N`; this is correct for
     every unsatisfiable formula, and for a satisfiable one it assumes that Siriaisa's ratio on the graph is at most
     `2N`.

`s SATISFIABLE` is printed only after the assignment has been checked to be consistent and to contain a literal of
every clause of the input (a final certification gate in `algorithm.solve`). `s UNSATISFIABLE` comes from steps 1–3, from
the branching, or from the ratio-`2N` rule at depth 0. `algorithm.solve(formula, branch_depth=0)` gives the rule without
branching. Use `-l` to see each stage in `app.log`.

## What Is Proved and What Rests on the Conjecture

Write `N` and `m` for the variables and clauses of the residual formula, `bound` for the copies per clause vertex,
`n = 2N + m · bound` for the vertices of the MIDS graph `G`, and `i(G)` for its minimum independent dominating set size.
The proofs are in the Siriaisa paper (Section "Application to Boolean Satisfiability").

**Proved, without any conjecture.**

- *Structure of the graph.* An independent dominating set with no clause vertex holds exactly one of `v`, `−v` for every
  variable and is a satisfying assignment. One that holds a copy of a clause vertex holds all `bound` copies (they have
  the same neighbours), and then it has at least `bound + N` vertices. So `i(G) = N` if the formula is satisfiable,
  `i(G) ≥ bound + N` otherwise, and no independent dominating set has a size strictly between `N` and `bound + N`.
- *Two values of the ratio.* On the graph of a satisfiable formula, the ratio `|S| / i(G)` of any independent dominating
  set `S` is either exactly `1` (and `S` is a satisfying assignment) or at least `(bound + N) / N`, when `S` holds clause
  copies. With SatyPy's `bound` this is larger than `2N`, and with `bound_t` (below) larger than `n^(1−1/t)`, in
  particular larger than `n^(3/4)` for `t = 4`. So on these graphs a ratio of at most `2N` (or `n^(1−1/t)`) holds
  exactly when `S` is optimal.
- *Maximum satisfiability.* With `μ` the least number of clauses falsified by an assignment,
  `bound · μ ≤ i(G) ≤ bound · μ + N`, so `μ = ⌊i(G) / bound⌋`; every independent dominating set `D` holds the copies of
  exactly `⌊|D| / bound⌋` clauses and decodes to an assignment that falsifies at most that many.
- *The bound.* `reduction.mids_bound` returns `2N² − N + 1`, the least integer with `bound + N > 2N · N`; it satisfies
  `bound ≥ N + 1`, and the graph has at most `2N + 2mN²` vertices.
- *The answers.* Every unsatisfiable formula is answered `UNSATISFIABLE`, every `SATISFIABLE` answer carries a checked
  assignment, and the MIDS stage never answers `UNKNOWN`.
- *Branching.* Splitting on a clause is exact, and branching to depth `d` runs Siriaisa at most `1 + w + … + w^d` times
  (`w` the largest clause width), each time on the graph of a formula with at most `N` variables and `m` clauses, so it
  is polynomial for every fixed `d`. A satisfiable formula is answered `UNSATISFIABLE` only if there is a chain of
  `d + 1` satisfiable formulas, each obtained from the previous one by fixing a literal, on all of whose graphs
  Siriaisa's set contains clause vertices (ratio larger than `2N`).
- *What Siriaisa's proved bound does not give.* Siriaisa proves that its degree-splitting strategy gives at most
  `⌊√n⌋ · (i(G) + s(G))` vertices, where `s(G)` is the sum of `⌈deg(v)/k⌉ − 1` over the vertices of degree larger than
  `k = ⌊√n⌋`. Every graph satisfies `⌊√n⌋ · (i(G) + s(G)) ≥ n − i(G)`, so on the graph of a satisfiable formula the
  bound is at least `N + m · bound ≥ bound + N`, for every number of copies: it never shows that Siriaisa's set avoids
  the clause vertices.

**The conjecture: ratio `n^(1−ε)` with `ε = 1/4`.** The Siriaisa paper conjectures that Siriaisa's output satisfies
`|S| / i(G) ≤ n^(3/4)` on every graph; a proof would imply P = NP, since no polynomial-time algorithm has ratio
`n^(1−ε)` for any `ε > 0` unless P = NP (Halldórsson). The MIDS graph can be sized for any ratio `n^(1−1/t)`: with
`bound_t = N^t · (3m)^(t−1) + 1` copies per clause vertex, the graph has `n = 3^(t−1) N^t m^t + m + 2N` vertices,
`bound_t + N > N · n^(1−1/t)`, and every `n^(1−1/t)`-approximation decides satisfiability by `|S| < bound_t`. For
`ε = 1/4` (`t = 4`), `bound_4 = 27N⁴m³ + 1` and `n = 27N⁴m⁴ + m + 2N`: if the conjecture holds, the MIDS stage with
`bound_4` copies decides every CNF formula correctly in polynomial time. SatyPy uses the much smaller `bound` of step 4
(the ratio-`2N` rule), because the graph for `bound_4` grows as `27N⁴m⁴` and is too large to build except for very
small formulas; by the two values of the ratio, every choice of `bound` asks the same of Siriaisa on a satisfiable
formula: to return an optimal set.

## Running the Experiments

The folder `car/` contains two experiment scripts. Both run from the repository root (or from `car/`) with or without
SatyPy installed: they use the repository's own `satypy/`. Siriaisa (`pip install siriaisa`) must be installed.

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

For each formula it prints and writes the expected answer, SatyPy's answer, whether it is correct, and the deciding
stage; for formulas decided on the MIDS graph also the residual size, `bound`, the vertices and edges of the graph,
`|S|`, `|S| / N` against `2N`, whether `|S| ≥ bound + N` on unsatisfiable formulas, and the splitting excess `s(G)`
with `i(G) + s(G)` and `2N²`. The summary counts correct, wrong and unknown answers and lists every wrong one.

**`car/strategy_search.py`** uses formulas built to stress the MIDS stage: satisfiable formulas with a single planted
solution (`planted-unique`), satisfiable formulas that neither the all-True nor the all-False assignment satisfies
(`nonconstant`), and unsatisfiable formulas (`unsat`); it keeps only formulas whose residual formula reaches the MIDS
graph.

```bash
python car/strategy_search.py
python car/strategy_search.py --variables 4 7 --count 10 --seed 11
```

| Option | Meaning (default) |
|---|---|
| `--variables MIN MAX` | number of variables (3 6) |
| `--count C` | formulas per kind and number of variables (5) |
| `--max-clauses M` | largest number of clauses (16) |
| `--attempts A` | generation attempts per formula (2000) |
| `--seed S` | random seed (2026) |
| `-o FILE` | output CSV (`car/strategy_search_results.csv`) |

For each formula it prints and writes the number of satisfying assignments, SatyPy's answer and its correctness, the
deciding stage (`mids`, `mids (branching)`, `mids (ratio rule)`, ...), the size of every Siriaisa strategy `c1`–`c18`
on the formula's graph and which of them reach exactly `N` vertices, and a check of the maximum-satisfiability
statement: `⌊|S| / bound⌋ ≥ μ`, and the decoded assignment falsifies at most `⌊|S| / bound⌋` clauses. The summary counts
the answers by stage and the formulas on which each strategy is optimal.

**Testing a single formula.** Any DIMACS file can be checked against exhaustive search (`-b`, at most 30 variables) and
MiniSat 2.2 (`-a`), with the deciding stage in `app.log` (`-l`):

```bash
saty -i benchmarks/test_formulas/planted_unique_v6_2.cnf -a -b -l
test_saty -d 5 -m 12 -n 20 -r 7 -a -b -c
```

The MIDS graph has `2N + m · (2N² − N + 1)` vertices, about `2mN²`, and every branching level runs Siriaisa again on up
to `w` such graphs (`w` the largest clause width). For residual 3-CNF formulas with the sizes of some benchmarks:

| Size of | Variables | Clauses | `bound` | Vertices | Edges |
|---|---|---|---|---|---|
| `uf20-91` | 20 | 91 | 781 | 71,111 | 213,233 |
| `aim-50-1_6` | 50 | 80 | 4,951 | 396,180 | 1,188,290 |
| `aim-100-1_6` | 100 | 160 | 19,901 | 3,184,360 | 9,552,580 |
| `aim-200-2_0` | 200 | 400 | 79,801 | 31,920,800 | 95,761,400 |

## References

- R. M. Karp, *Reducibility among combinatorial problems*, 1972; M. R. Garey and D. S. Johnson, *Computers and
  Intractability*, Freeman, 1979.
- B. Aspvall, M. F. Plass and R. E. Tarjan, *A linear-time algorithm for testing the truth of certain quantified
  Boolean formulas*, Inform. Process. Lett. 8 (1979) 121–123.
- F. Vega, [Siriaisa 0.0.8](https://pypi.org/project/siriaisa/), and *The Siriaisa Algorithm for Minimum Independent
  Dominating Set* (manuscript; Section "Application to Boolean Satisfiability" contains the proofs above).
- M. M. Halldórsson, *Approximating the minimum maximal independence number*, Inform. Process. Lett. 46 (1993) 169–172.

## Implementation

- **Programming Language:** Python
- **Author:** Frank Vega

## License

This code is released under the MIT License.

# SatyPy: SAT Solver through Minimum Independent Dominating Set

![SatyPy: SAT Solver](docs/satypy.png)

This work builds upon [SatyPy: SAT Solver](https://github.com/frankvegadelgado/satypy).

SatyPy decides Boolean formulas in CNF by reducing them to **Minimum Independent Dominating Set** (MIDS) and solving the MIDS instance with
[Siriaisa](https://pypi.org/project/siriaisa/) 0.0.8. The decision rule is based on the conjecture that Siriaisa has an
approximation ratio of `2√n`. Every `SATISFIABLE` comes with a checked assignment, and every unsatisfiable formula is
answered `UNSATISFIABLE` (both are proved, without the conjecture). The only answer that can be wrong is
`UNSATISFIABLE` on a satisfiable formula, and that would be a counterexample to the conjecture (see
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

- **Unsatisfiable:** `s UNSATISFIABLE`, when an exact stage proves it or when Siriaisa's independent dominating set
  has more than `2√n · N` vertices. Every unsatisfiable formula receives this answer; on a satisfiable formula it can
  only appear if Siriaisa's ratio exceeds `2√n` (`2√n` conjecture, see below).

- **Comment lines:** before the answer, SatyPy prints DIMACS comment lines (`c ...`) that report what Siriaisa found
  on the MIDS graph and, when the formula is decided, a line `c decided by: ...` naming the stage that decided it
  (empty clause, simplification, 2-SAT, MIDS graph, or MIDS graph under the `2*sqrt(n)` conjecture).

- **Undecided:** `s UNKNOWN`, preceded by the comment lines. It is printed only when a certification check rejects an
  assignment, which the proofs below show cannot happen at the MIDS stage.

## Examples

The directory `benchmarks/test_formulas` contains four small formulas.

```
saty -i benchmarks/test_formulas/formula2.cnf
saty -i benchmarks/test_formulas/formula3.cnf
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
   `bound = 2mN² + ⌊√(4m²N⁴ + 8N³ − 4mN³)⌋ + 1 − N` (`reduction.mids_bound`) is the least integer with
   `bound + N > 2√n · N` for the number of vertices `n = 2N + m · bound`. The formula is satisfiable if and only if
   the graph has an independent dominating set of `N` vertices (one endpoint of each edge `{v, −v}`); otherwise every
   independent dominating set contains all `bound` copies of some clause vertex. With the copies of exactly one
   clause it also contains an endpoint of each edge `{v, −v}` (a clause holds at most one of `v`, `−v`), so it has
   `bound + N` vertices; with the copies of two or more clauses it has at least `2 · bound ≥ bound + N` vertices.
   So it has more than `2√n · N` vertices.
5. **Siriaisa** 0.0.8 (`siriaisa.algorithm.find_independent_dominating_set`) computes an independent dominating set `S`:
   - if `|S| < bound`, `S` contains no clause vertex, and `reduction.decode_mids` reads an assignment from it, which is
     verified against the input (`s SATISFIABLE`);
   - if `|S| > 2√n · N`, the formula is reported unsatisfiable (`s UNSATISFIABLE`); this is correct for every
     unsatisfiable formula, and for satisfiable formulas it rests on the conjecture that Siriaisa's approximation
     ratio is at most `2√n`;
   - the remaining case (`bound ≤ |S| ≤ 2√n · N`) never occurs: an independent dominating set has either `N` or at
     least `bound + N > 2√n · N` vertices.

`s SATISFIABLE` is printed only after the assignment has been checked to be consistent and to contain a literal of
every clause of the input (a final certification gate in `algorithm.solve`). `s UNSATISFIABLE` comes from steps 1–3 or
from step 5. Use `-l` to see each stage in `app.log`.

## What Is Proved and What Rests on the Conjecture

Write `N` and `m` for the variables and clauses of the residual formula, `bound` for the copies per clause vertex,
`n = 2N + m · bound` for the vertices of the MIDS graph `G`, and `i(G)` for its minimum independent dominating set size.

**Proved, without any conjecture.**

- *Structure of the graph.* An independent dominating set with no clause vertex holds exactly one of `v`, `−v` for every
  variable and is a satisfying assignment. One that holds a copy of a clause vertex holds all `bound` copies (they have
  the same neighbours), and then it has at least `bound + N` vertices. So `i(G) = N` if the formula is satisfiable,
  `i(G) ≥ bound + N` otherwise, and no independent dominating set has a size strictly between `N` and `bound + N`.
  The value `bound + N` is attained when some assignment falsifies exactly one clause (all 8 sign patterns of 3
  variables, `formula3.cnf`, is an example).
- *The bound.* `reduction.mids_bound` returns the least integer with `bound + N > 2√n · N`; it satisfies
  `N ≤ bound ≤ 4mN² + 1`, so the graph has at most `2N + 4m²N² + m` vertices.
- *The answers.* If `|S| < bound`, `S` decodes to a satisfying assignment that passes the check. Otherwise
  `|S| ≥ bound + N > 2√n · N`, so the answer is `UNSATISFIABLE`: the MIDS stage never answers `UNKNOWN`, and every
  unsatisfiable formula is answered `UNSATISFIABLE`.
- *The only possible error.* On a satisfiable formula the answer is `UNSATISFIABLE` exactly when Siriaisa's set
  contains a clause vertex, and then its ratio is at least `(bound + N)/N > 2√n`.

**Resting on the conjecture.** If Siriaisa's ratio is at most `2√n` on these graphs, a satisfiable formula gives
`|S| ≤ 2√n · N < bound + N`, so `S` has no clause vertex and SatyPy answers `SATISFIABLE` with a checked assignment.
Then SatyPy would decide every CNF formula correctly in polynomial time, which would imply P = NP; this is why the
`2√n` ratio is stated as a conjecture.

**What Siriaisa's proved bound does not give.** Siriaisa proves that its degree-splitting strategy gives at most
`⌊√n⌋ · (i(G) + s(G))` vertices, where `s(G)` is the sum of `⌈deg(v)/k⌉ − 1` over the vertices of degree larger than
`k = ⌊√n⌋`, and that the output satisfies the same bound when the decoded set is independent. On the MIDS graph a
literal that occurs `occ` times has degree `1 + bound · occ` and `bound/k ≈ 2N`, so `s(G) ≈ 2N · L`, where `L` is the
number of literal occurrences of the residual formula (pure literals are removed in step 2, so `L ≥ 2N` and
`s(G) > 4N² − 2N²/k − 2N`). The proved bound therefore lies far above the decision threshold `2√n · N`: on
`formula2.cnf` (`N = 3`, `m = 7`, `n = 1,735`), `s(G) = 126` and the bound is `⌊√n⌋ · (N + s(G)) = 5,289`, against a
threshold of `249.9`. Converting the formula to 3CNF first does not change this. More generally, every graph satisfies

```
⌊√n⌋ · (i(G) + s(G)) ≥ n − i(G)
```

(a minimum independent dominating set `D` dominates the other `n − i(G)` vertices, so the degrees of `D` add up to at
least `n − i(G)`, and each `d` in `D` contributes at least `deg(d)/k − 1` to `s(G)`). So for any reduction with
`i = a` on satisfiable and `i ≥ b` on unsatisfiable formulas, the proved bound separates them only if `b > n − a`,
which forces the unsatisfiable graphs to have maximum degree below `a` and fewer than `a²` edges, while the satisfiable
ones have at least `n − a` edges.

The correct `SATISFIABLE` answers therefore come from Siriaisa's actual output, not from this bound: in
`car/small_formulas.py` (187 formulas, 117 decided on the MIDS graph), Siriaisa returned `|S| = N` on all 114
satisfiable instances, and every answer agreed with exhaustive search.

**Checking on small formulas.** `car/small_formulas.py` decides very small random formulas and the small DIMACS files of
`benchmarks` with SatyPy and with exhaustive search, compares the answers, and reports, for the formulas decided on the
MIDS graph, `|S|` against `2√n · N`, whether `|S| ≥ bound + N` on unsatisfiable formulas, and `s(G)`. It runs from the
repository root with or without SatyPy installed:

```bash
python car/small_formulas.py
python car/small_formulas.py --variables 3 6 --clauses 16 --repeat 10 --seed 7
```

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

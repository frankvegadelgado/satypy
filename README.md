# SatyPy: SAT Solver through Minimum Independent Dominating Set

![SatyPy: SAT Solver](docs/satypy.png)

This work builds upon [SatyPy: SAT Solver](https://github.com/frankvegadelgado/satypy).

SatyPy decides Boolean formulas in CNF by reducing them directly to **Minimum Independent Dominating Set** (MIDS): a vertex for
every literal and for every clause, one independence edge between the two literals of each variable, and each clause
adjacent to its literals. An independent dominating set of this graph without clause vertices is exactly a satisfying
assignment: one literal per variable (the independence edge) and every clause dominated by a true literal. SatyPy asks the
MIDS search of Siriaisa (`satypy.siriaisa`) for such a set, with the clause vertices as its forbidden vertices. Every
`SATISFIABLE` comes with a checked assignment. `UNSATISFIABLE` is printed when an exact stage proves it, when every branch is
proved unsatisfiable, or, if `algorithm.ASSUME_SEARCH_COMPLETE` is True, at the deepest level, under the assumption that the
search finds such a set whenever one exists; with the assumption off (`ASSUME_SEARCH_COMPLETE = False`) the answer there is
`UNKNOWN` (see [What Is Proved and What Is Assumed](#what-is-proved-and-what-is-assumed)).

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
  set found by the search is unsatisfiable, or, at the deepest level, when the search leaves vertices undominated and
  `algorithm.ASSUME_SEARCH_COMPLETE` is True (the default; this answer is an assumption, not a proof).

- **Comment lines:** before the answer, SatyPy prints DIMACS comment lines (`c ...`) that report what the MIDS stage
  found and, when the formula is decided, a line `c decided by: ...` naming the stage that decided it (empty clause,
  simplification, XOR constraints, 2-SAT, MIDS graph, branching, or MIDS graph under the assumption).

- **Undecided:** `s UNKNOWN`, preceded by the comment lines. It is printed when the assignment of a set that dominates every
  vertex does not satisfy the formula, or, only with `ASSUME_SEARCH_COMPLETE = False`, when the search leaves vertices
  undominated and branching decides nothing.

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
3. **XOR constraints** (`affine.implied_clauses`, on the formula given to `solve` only, when a clause of the residual
   formula has more than two literals): `2^(k-1)` clauses over the same `k` variables (`2 ≤ k ≤ 5`) whose falsifying
   assignments all have the same parity are the equation `x_1 + … + x_k = b` (mod 2), wherever they occur in the
   formula. The equations form a linear system over GF(2), which is eliminated with a fixed bound on the work
   (`affine.GAUSS_WORK`; the stage is skipped when the bound is passed). An inconsistent system proves the formula
   unsatisfiable. Otherwise the equations of at most three variables that follow from the system (a variable fixed, two
   variables equal or opposite, the parity of three) are added as clauses, which the formula implies, and unit
   propagation runs again. A formula without XOR constraints is not changed.
4. **2-SAT**: if every remaining clause has at most two literals, the formula is decided exactly by the
   strongly-connected-components algorithm (`algorithm._solve_two_sat`).
5. **Reduction to MIDS** (`reduction.reduce_cnf_to_mids`): the residual formula is used as it is. For each variable `v`
   there are the vertices `(v)` and `(¬v)`, joined by an *independence edge*, and each clause `i` is a vertex adjacent to
   the vertices of its literals. There is no other edge. With `N` the number of variables, the graph has `2N` literal
   vertices and one vertex per clause.
6. **MIDS search with forbidden vertices** (`siriaisa.algorithm.find_independent_dominating_set` with the clause vertices as
   `forbidden`, implemented by `siriaisa.forbidden_search`): a weighted local search over independent sets without clause
   vertices. It starts from a random maximal independent set of the literal vertices (one literal per variable) and
   minimises the weight of the undominated vertices. A step picks a random undominated vertex and inserts the vertex of its
   closed neighbourhood (a literal vertex) that decreases the weight most, evicting its neighbours in the set (the opposite
   literal); with probability 0.02 a random candidate is taken instead. After every step the weight of every undominated
   vertex grows by one (halved when the mean exceeds 50), and the work is bounded by `max(50(n + m), 400000)` units, so
   the search is linear for fixed parameters. It returns the independent set with fewest undominated vertices that it met;
   the set is a dominating set exactly when it leaves none. The search of the formula given to `solve` (which runs once) gets `max(1 + 2d, R/10)` times that work, `d` being the branching depth and `R` the number of searches that the whole branching runs at most (so the extra work is at most a tenth of the work of the branching); the searches of the branches get the work above. Then:
   - if it leaves no vertex undominated, `reduction.decode_mids` reads the literals of its vertices; the completed
     assignment is verified against the input (`s SATISFIABLE`), and if it does not satisfy the formula the answer is
     `s UNKNOWN`;
   - otherwise step 7 runs.
7. **Branching on a clause falsified by the set found by the search** (`algorithm._branch`, up to depth
   `d = max(2, ⌊log₃(m + n)⌋)`, `algorithm.default_branch_depth`, with `m` clauses and `n` variables in the input): the
   literals of the set, completed with False, either satisfy the formula (`s SATISFIABLE`) or falsify some clauses.
   SatyPy takes a shortest falsified clause `C` and decides every formula `φ ∧ ℓ`, `ℓ ∈ C`, with steps 2 and 4–7 and one level
   less: the formula implies `C`, so it is satisfiable exactly when some branch is.
   - some branch satisfiable: `s SATISFIABLE`, with the checked assignment of that branch;
   - every branch unsatisfiable: `s UNSATISFIABLE`;
   - at depth 0 (no branching left): `s UNSATISFIABLE` if `algorithm.ASSUME_SEARCH_COMPLETE` is True, `s UNKNOWN`
     otherwise.

`s SATISFIABLE` is printed only after the assignment has been checked to be consistent and to contain a literal of
every clause of the input (a final certification gate in `algorithm.solve`). `s UNSATISFIABLE` comes from steps 1–4, from
the branching, or from the assumption at depth 0. `algorithm.solve(formula, branch_depth=0)` gives the answer without
branching. Use `-l` to see the stages of the formula in `app.log`; the answer is also printed on the console.

## What Is Proved and What Is Assumed

Write `N` for the number of variables of the residual formula and `G` for its MIDS graph (one vertex per clause).

**Proved.**

- *The graph.* The two literal vertices of a variable are adjacent and are the only edge between literal vertices; a
  clause vertex is adjacent only to the literal vertices of its literals. Each literal vertex dominates the pair of its
  variable.
- *Independent dominating sets without clause vertices.* Let `S` be an independent dominating set of `G` with no clause
  vertex. The two literals of a variable are adjacent, so `S` holds at most one of them, and it holds at least one
  because the literal vertices of the variable must be dominated and only literal vertices are in `S`; so `S` is one
  literal per variable, and every clause vertex is adjacent to a vertex of `S`, a true literal of that clause. Conversely
  an assignment gives such a set. So `G` has an independent dominating set without clause vertices exactly when the
  formula is satisfiable, and its size is then `N`.
- *The XOR constraints.* `2^(k-1)` clauses over `k` variables whose falsifying assignments all have the same parity
  forbid exactly the assignments of that parity, so they are the equation `x_1 + … + x_k = b` (mod 2). If the
  linear system of the equations of a formula is inconsistent, the formula is unsatisfiable; every equation that
  follows from the system holds in every model, so the clauses of such an equation are implied by the formula and
  adding them changes neither its models nor its satisfiability.
- *The answers.* Every `SATISFIABLE` answer carries a checked assignment. `UNSATISFIABLE` comes from the exact stages
  1–4, from branching when every branch is unsatisfiable, or, at depth 0, from the assumption below.
- *Branching.* Splitting on a clause is exact, and branching to depth `d` runs the MIDS stage at most
  `1 + w + … + w^d` times (`w` the largest clause width). With `d = max(2, ⌊log₃(m + n)⌋)` and `w = 3` that is
  `(3^(d+1) − 1)/2 ≤ max(13, 3(m + n)/2)` runs.

**Not proved.**

- *The assumption.* `UNSATISFIABLE` at depth 0 assumes that the search finds an independent dominating set without clause
  vertices whenever one exists. Deciding whether one exists is deciding satisfiability, so the search is a heuristic and
  this answer is not a proof; `ASSUME_SEARCH_COMPLETE = False` turns it into `UNKNOWN`.

## Running the Experiments

The folder `car/` contains three experiment scripts. All run from the repository root (or from `car/`) with or without
SatyPy installed: they use the repository's own `satypy/` (Siriaisa included). `networkx` must be installed, and
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
and, for the formulas that reach the MIDS graph, its vertices, edges, maximum degree, the size of the set found by the search and the number of vertices it leaves undominated. The summary counts correct,
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
vertices of the MIDS graph, the size of the set found by the search, the vertices it leaves undominated and both running times.

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
- Y. Cai, K. Su, C. Luo and A. Sattar, *NuMVC: An efficient local search algorithm for minimum vertex cover*, J. Artif. Intell. Res. 46 (2013) 687–716.

## Implementation

- **Programming Language:** Python
- **Author:** Frank Vega

## License

This code is released under the MIT License.

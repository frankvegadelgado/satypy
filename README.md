# SatyPy: SAT Solver through Unique Games and Vertex Cover

![SatyPy: SAT Solver](docs/satypy.png)

This work builds upon [SatyPy: SAT Solver](https://github.com/frankvegadelgado/satypy).

SatyPy decides Boolean formulas in CNF by reducing them to **Minimum Vertex Cover** and solving the vertex cover
instances with [Salvador](https://pypi.org/project/salvador/) 0.1.0. It implements two reductions from 3SAT to Vertex
Cover: Karp's exact reduction, and the gap reduction behind the Unique Games Theorem reported by the OpenAI Math Team in
October 2026 (Result Family 102, [openai/math](https://github.com/openai/math/blob/main/lean/docs/102.md)), composed with
the Vertex Cover reduction of Khot and Regev. **SatyPy never gives a wrong answer**: every `SATISFIABLE` comes with a
checked assignment (or, for the gap rule, a proved bound), every `UNSATISFIABLE` comes from an exact argument, and
everything else is `UNKNOWN`.

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

- **Satisfiable, without an assignment:** `s SATISFIABLE` with no `v` line. Only the gap rule of the Unique Games
  chain can produce it, and only with parameters for which the reference proves its bound (see below); in practice it
  never runs.

- **Unsatisfiable:** `s UNSATISFIABLE`, only when an exact stage proves it.

- **Comment lines:** before the answer, SatyPy prints DIMACS comment lines (`c ...`) that report what Salvador found
  on each Vertex Cover graph and, when the formula is decided, a line `c decided by: ...` naming the stage that decided
  it (empty clause, simplification, 2-SAT, OpenAI/Khot-Regev chain, gap rule, or Karp graph).

- **Undecided:** `s UNKNOWN`, preceded by the comment lines, for example:

  ```
  c OpenAI/Khot-Regev chain: 12672 vertices; Salvador cover: 8448 vertices (fraction 2/3; satisfiable formulas admit 2/3); gap rule inactive: parameters t=1, h=1, rank-one gadget are below the reference's (t >= 7,097,828, h >= 2, latent gadget)
  c Karp graph: 30 vertices; Salvador cover: 20 vertices, 1 above the bound n + 2m = 19 (satisfiability not determined)
  s UNKNOWN
  ```

## Examples

The directory `benchmarks/test_formulas` contains four small formulas.

```
saty -i benchmarks/test_formulas/formula2.cnf
c OpenAI/Khot-Regev chain: 11232 vertices; Salvador cover: 7488 vertices (fraction 2/3; satisfiable formulas admit 2/3); gap rule inactive: parameters t=1, h=1, rank-one gadget are below the reference's (t >= 7,097,828, h >= 2, latent gadget)
c decided by: Karp graph (Salvador's cover is optimal, 17 vertices)
s SATISFIABLE
v 1 2 -3 0
```

`formula2.cnf` (3 variables, 7 clauses) survives simplification. The OpenAI/Khot–Regev chain runs first and does not
decide it; Salvador finds an optimal cover of its Karp graph, which is a satisfying assignment.

```
saty -i benchmarks/test_formulas/formula3.cnf
c OpenAI/Khot-Regev chain: 12672 vertices; Salvador cover: 8448 vertices (fraction 2/3; satisfiable formulas admit 2/3); gap rule inactive: parameters t=1, h=1, rank-one gadget are below the reference's (t >= 7,097,828, h >= 2, latent gadget)
c Karp graph: 30 vertices; Salvador cover: 20 vertices, 1 above the bound n + 2m = 19 (satisfiability not determined)
s UNKNOWN
```

`formula3.cnf` contains all eight sign patterns of three variables and is unsatisfiable. No stage of SatyPy can
refute it: a vertex cover never proves unsatisfiability.

```
batch_saty -i benchmarks/test_formulas -a -b -c
Test: formula0.cnf
formula0.cnf: (MiniSat) SATISFIABLE
formula0.cnf: (Brute Force) SATISFIABLE
formula0.cnf: (SatyPy) SATISFIABLE
...
Test: formula3.cnf
formula3.cnf: (MiniSat) UNSATISFIABLE
formula3.cnf: (Brute Force) UNSATISFIABLE
formula3.cnf: c OpenAI/Khot-Regev chain: ...
formula3.cnf: c Karp graph: 30 vertices; Salvador cover: 20 vertices, 1 above the bound n + 2m = 19 (satisfiability not determined)
formula3.cnf: (SatyPy) UNKNOWN
```

## Command-Line Options

To view the available command-line options for the `saty` command, use the following command in your terminal or command prompt:

```bash
saty -h
```

This will display the help message, which provides information about the available options and their usage:

```bash
usage: saty [-h] -i INPUTFILE [-a] [-b] [-c] [-m MAX_CLAUSES] [-e MAX_EXACT] [-v] [-t] [-l] [--version]

Solve the Boolean Satisfiability (SAT) problem using a DIMACS file as input.

options:
  -h, --help            show this help message and exit
  -i INPUTFILE, --inputFile INPUTFILE
                        Input file path
  -a, --approximation   enable comparison with a known SAT solver (MiniSat 2.2 via python-sat)
  -b, --bruteForce      enable comparison with the exponential-time brute-force approach (at most 30 variables)
  -c, --count           only state whether the formula is SATISFIABLE, UNSATISFIABLE or UNKNOWN
  -m MAX_CLAUSES, --max_clauses MAX_CLAUSES
                        largest 3-SAT formula sent to the Unique Games Vertex Cover stage (about 1,900
                        vertices, 11,800 edges and 24 MB per clause; 0 skips it; default: 100)
  -e MAX_EXACT, --max_exact MAX_EXACT
                        largest 3-SAT formula sent to the exact (Garey-Johnson) Vertex Cover stage
                        (3 vertices per clause; default: 100000)
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
    -m MAX_CLAUSES, --max_clauses MAX_CLAUSES: Larger 3-SAT formulas skip the Unique Games Vertex Cover stage (0 always skips it).
    -e MAX_EXACT, --max_exact MAX_EXACT: Larger 3-SAT formulas skip the exact (Garey-Johnson) Vertex Cover stage.
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
usage: batch_saty [-h] -i INPUTDIRECTORY [-a] [-b] [-c] [-m MAX_CLAUSES] [-e MAX_EXACT] [-v] [-t] [-l] [--version]

Solve the Boolean Satisfiability (SAT) problem using a directory with DIMACS files as input.

options:
  -h, --help            show this help message and exit
  -i INPUTDIRECTORY, --inputDirectory INPUTDIRECTORY
                        Input directory path
  -a, --approximation   enable comparison with a known SAT solver (MiniSat 2.2 via python-sat)
  -b, --bruteForce      enable comparison with the exponential-time brute-force approach (at most 30 variables)
  -c, --count           only state whether each formula is SATISFIABLE, UNSATISFIABLE or UNKNOWN
  -m MAX_CLAUSES, --max_clauses MAX_CLAUSES
                        largest 3-SAT formula sent to the Unique Games Vertex Cover stage (0 skips it; default: 100)
  -e MAX_EXACT, --max_exact MAX_EXACT
                        largest 3-SAT formula sent to the exact (Garey-Johnson) Vertex Cover stage (default: 100000)
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
usage: test_saty [-h] -d DIMENSION [-m CLAUSES] [-k WIDTH] [-n NUM_TESTS] [-g] [-r SEED] [-a] [-b] [-c] [-w] [-M MAX_CLAUSES] [-e MAX_EXACT] [-v] [-l] [--version]

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
  -M MAX_CLAUSES, --max_clauses MAX_CLAUSES
                                        largest 3-SAT formula sent to the Unique Games Vertex Cover stage (0 skips it; default: 100)
  -e MAX_EXACT, --max_exact MAX_EXACT   largest 3-SAT formula sent to the exact (Garey-Johnson) Vertex Cover stage (default: 100000)
  -v, --verbose                         enable verbose output
  -l, --log                             enable file logging
```

Example:

```
test_saty -d 6 -m 12 -n 8 -g -r 7 -a -b -c
1-MiniSat Test: SATISFIABLE
1-Brute Force Test: SATISFIABLE
1-SatyPy Test: UNKNOWN
...
Summary: 1 SATISFIABLE (verified), 0 UNSATISFIABLE, 7 UNKNOWN, 0 disagreements
```

## How SatyPy Solves a Formula

Variable IDs may be any positive integers (not necessarily `1..n`, contiguous, or sorted).

1. **Empty clause**: a formula containing the empty clause (a lone `0` in DIMACS) is unsatisfiable.
2. **Simplification** (`reduction.reduce_sat_to_simplified_sat`): unit propagation and pure literals. A conflict proves the
   formula unsatisfiable.
3. **2-SAT**: if every remaining clause has at most two literals, the formula is decided exactly by the
   strongly-connected-components algorithm (`algorithm._solve_two_sat`).
4. **OpenAI/Khot–Regev chain** (at most `-m` 3-SAT clauses): otherwise `reduction.reduce_sat_to_3sat` converts the
   residual formula to exactly three literals per clause, and `reduction.reduce_3sat_to_unweighted_vertex_cover`
   implements the gap reduction of the reference,

   ```
   3SAT → weighted parity (exact 10-equation gadget) → translation Unique Game (matrix test, OpenAI 2026, §4)
        → unweighted simple bipartite game (rounding + subdivision, Lemma 7.1) → parallel repetition
        → strong-left form (Khot–Regev) → p-biased Vertex Cover graph (Khot–Regev 2008) → unweighted graph
   ```

   then runs Salvador. With `p = 1/3` a satisfiable formula admits a cover of 2/3 of the vertices (threshold ratio 1.5).
   Two ways of concluding are implemented:
   - the **gap rule** (`reduction.gap_rule`): if unsatisfiable formulas provably need covers of at least a fraction
     `b` of the vertices and Salvador's cover is smaller, the formula is satisfiable and SatyPy prints
     `s SATISFIABLE` without a `v` line. It runs only when the parameters meet the reference
     (`reduction.reference_parameters_met`: the latent gadget of Lemma 3.1, repetition exponent
     `t ≥ 10,240,000 ln 2 ≈ 7,097,828`, sequence length `h ≥ 2`) and refuses otherwise. Such instances have at least
     `4^7,097,828` edges and cannot be stored, so the rule never runs in practice;
   - **decoding** (`reduction.decode_vertex_cover_to_assignment`) of Salvador's cover into an assignment, which is
     then verified.

   At the parameters that fit in memory (`p = 1/3`, `ℓ = k = t = h = 1`) the graph is a disjoint union of copies of
   one 18-vertex graph whose minimum cover is 12, for every formula, so this stage cannot tell satisfiable and
   unsatisfiable formulas apart (see Experiments below).

5. **Exact reduction to Vertex Cover** (at most `-e` 3-SAT clauses): `reduction.reduce_3sat_to_exact_vertex_cover` builds Karp's graph in the form of Garey
   and Johnson (an edge per variable, a triangle per clause, an edge from each corner to its literal; `2n + 3m` vertices).
   The formula is satisfiable if and only if this graph has a vertex cover of `n + 2m` vertices, and every cover has at
   least that many. [Salvador](https://pypi.org/project/salvador/) 0.1.0 computes a cover; if it has exactly `n + 2m`
   vertices it is optimal and `reduction.decode_exact_vertex_cover` reads a satisfying assignment from it.
Both Vertex Cover stages run on every formula that reaches them. **The chain has priority**: when it decides the
formula its answer is printed (followed by `c also decided by: Karp graph ...` if Karp decided it too); otherwise
Karp's answer is printed. A `c decided by: ...` line always names the stage that decided the formula.

When a Vertex Cover stage runs without deciding, SatyPy prints DIMACS comment lines before `s UNKNOWN`, for example:

```
c OpenAI/Khot-Regev chain: 12672 vertices; Salvador cover: 8448 vertices (fraction 2/3; satisfiable formulas admit 2/3); gap rule inactive: parameters t=1, h=1, rank-one gadget are below the reference's (t >= 7,097,828, h >= 2, latent gadget)
c Karp graph: 30 vertices; Salvador cover: 20 vertices, 1 above the bound n + 2m = 19 (satisfiability not determined)
s UNKNOWN
```

**SatyPy never gives a wrong answer.** `s SATISFIABLE` is printed only after the assignment has been checked to be
consistent and to contain a literal of every clause of the input (a final certification gate in `algorithm.solve`), and
`s UNSATISFIABLE` only when steps 1–3 prove it; `s SATISFIABLE` without an assignment only from the gap rule, with
parameters for which the reference proves the bound. Everything else is `s UNKNOWN`. In particular a vertex cover is never used
to conclude unsatisfiability: that would need a certified lower bound above `n + 2m`, which Salvador does not provide.
So unsatisfiable formulas that steps 1–3 cannot refute, and satisfiable formulas on which Salvador's cover is not exactly
optimal, are reported as `UNKNOWN`. Use `-l` to see each stage in `app.log`.

References: OpenAI Math Team, *The Unique Games Conjecture and Optimal Approximation Thresholds* (Result Family 102,
[openai/math](https://github.com/openai/math/blob/main/lean/docs/102.md), 2026); S. Khot and O. Regev, *Vertex cover
might be hard to approximate to within 2 − ε*, J. Comput. System Sci. 74 (2008) 335–349.

## Experiments

All numbers below were measured with SatyPy 0.0.2, which ran the Karp stage before the chain, and Salvador 0.1.0 (defaults) on a machine with 2 CPU cores and
8 GB of memory. Python randomises the iteration order of hashed objects from one run to the next, which can change
Salvador's tie-breaking, so counts may vary slightly between runs; the soundness of the answers cannot.

**Soundness.** On 5,000 random formulas with 1 to 12 variables (non-contiguous identifiers, clause widths 1 to 5,
duplicate literals, tautologies, unit clauses, occasional empty clauses), compared with exhaustive search, SatyPy
returned a checked assignment for 2,809 of the 2,813 satisfiable formulas, proved 2,152 of the 2,187 unsatisfiable ones,
and answered `UNKNOWN` on 39. **No answer was wrong.**

**Karp stage on random 3SAT** (`test_saty -d n -m m -n 50 -r 1 -g -a -c -M 0`, 50 formulas per size): SatyPy found and
checked an assignment for

| Variables | Clauses | Satisfiable (MiniSat) | Solved by SatyPy | Wrong |
|---|---|---|---|---|
| 10 | 30 | 50 | 47 | 0 |
| 12 | 51 | 37 | 16 | 0 |
| 20 | 80 | 43 | 11 | 0 |
| 30 | 120 | 42 | 5 | 0 |
| 50 | 210 | 32 | 0 | 0 |

The Karp stage needs an *optimal* cover: a cover one vertex above `n + 2m` reveals nothing, and near the satisfiability
threshold Salvador's cover is more often one or more vertices above it as formulas grow.

**OpenAI/Khot–Regev chain on very small formulas.** The chain was run at its default parameters (`p = 1/3`, `ℓ = k = t = h = 1`) on 35
very small 3SAT formulas: the two 3SAT formulas of `benchmarks/test_formulas`, 27 random formulas with 3 to 5 variables
and 4 to 12 clauses (all satisfiable), and 6 random unsatisfiable formulas with 3 or 4 variables and 16 clauses, giving
Vertex Cover graphs of 6,912 to 24,840 vertices and 43,008 to 154,560 edges (at most 36 seconds per formula, Salvador
included).

| Measurement | Result |
|---|---|
| Graph size equals the proved `36·\|E(H)\|` vertices and `224·\|E(H)\|` edges | 35 of 35 |
| Salvador's cover equals the proved optimum `2N/3` (ratio exactly 1) | 35 of 35 |
| Cover built from a satisfying assignment (completeness of the chain) | 28 of 28 satisfiable, 0.6875–0.6889 of the vertices |
| Decoding that cover gives back a satisfying assignment (round trip) | 28 of 28 |
| Decoding Salvador's cover gives a satisfying assignment | 6 of 28 (a blind random guess would succeed on 9.7 on average) |
| Unsatisfiable formulas whose optimal cover differs from `2N/3` | 0 of 7 |
| Gap rule applicable | 0 of 35 (parameters below the reference's) |
| SatyPy's final answer | 28 `SATISFIABLE` (23 from the Karp stage, 5 from simplification), 7 `UNKNOWN`, 0 wrong |

So, at sizes that can be built, the chain behaves exactly as its completeness argument says (a satisfying assignment
gives a cover of about 0.688 of the vertices, and the decoder inverts it), and Salvador always reaches the optimum 2/3.
But unsatisfiable formulas reach the same 2/3, and Salvador's optimal cover decodes to a satisfying assignment no more
often than chance: at these parameters the chain carries no information about satisfiability, and every decision above
was made by simplification or by the Karp stage.

## Formulas Decided by the OpenAI Chain

With the chain first (SatyPy 0.0.3), some satisfiable formulas are decided by it. Three examples, with the real output:

1. The formula that SatyPy 0.0.1 reported as solved through the chain (the fourth formula of
   `test_saty -d 6 -m 12 -n 8 -g -r 7`, with non-contiguous identifiers):

   ```
   p cnf 59 12
   -31 -58 23 0
   59 -23 -42 0
   -23 58 31 0
   -59 52 -23 0
   -23 42 59 0
   58 -31 -59 0
   59 -31 -42 0
   -42 58 -23 0
   -23 -52 58 0
   -59 -52 -31 0
   59 -58 -52 0
   -42 52 -23 0
   ```

   ```
   c OpenAI/Khot-Regev chain: 20808 vertices; Salvador cover: 13872 vertices (fraction 2/3; satisfiable formulas admit 2/3); gap rule inactive: parameters t=1, h=1, rank-one gadget are below the reference's (t >= 7,097,828, h >= 2, latent gadget)
   c decided by: OpenAI/Khot-Regev chain (decoded assignment; 6 of 6 variables decided by the cover, the rest set to False; verifier accepted the complement of the assignment); note: all False also satisfies the formula
   c also decided by: Karp graph (Salvador's cover is optimal)
   s SATISFIABLE
   v -23 -31 -42 -52 -58 -59 0
   ```

2. A formula satisfied by the all-True assignment (`p cnf 3 4`: `-1 3 -2 0`, `2 3 1 0`, `-3 2 1 0`, `2 1 3 0`):

   ```
   c OpenAI/Khot-Regev chain: 6912 vertices; Salvador cover: 4608 vertices (fraction 2/3; satisfiable formulas admit 2/3); gap rule inactive: parameters t=1, h=1, rank-one gadget are below the reference's (t >= 7,097,828, h >= 2, latent gadget)
   c decided by: OpenAI/Khot-Regev chain (decoded assignment; 3 of 3 variables decided by the cover, the rest set to False; verifier accepted the assignment); note: all True also satisfies the formula
   c also decided by: Karp graph (Salvador's cover is optimal)
   s SATISFIABLE
   v 1 2 3 0
   ```

3. A formula satisfied by the all-False assignment (`p cnf 3 6`: `2 3 -1 0`, `-3 1 2 0`, `-2 -3 -1 0`, `3 -1 2 0`,
   `1 -2 3 0`, `2 3 -1 0`):

   ```
   c OpenAI/Khot-Regev chain: 9792 vertices; Salvador cover: 6528 vertices (fraction 2/3; satisfiable formulas admit 2/3); gap rule inactive: parameters t=1, h=1, rank-one gadget are below the reference's (t >= 7,097,828, h >= 2, latent gadget)
   c decided by: OpenAI/Khot-Regev chain (decoded assignment; 3 of 3 variables decided by the cover, the rest set to False; verifier accepted the complement of the assignment); note: all False also satisfies the formula
   c also decided by: Karp graph (Salvador's cover is optimal)
   s SATISFIABLE
   v -1 -2 -3 0
   ```

**What these examples show.** In a search over random satisfiable formulas with 3 to 6 variables and 4 to 10 clauses
that survive simplification, the chain decided 28 of 40; **every one of the 28 is satisfied by the all-True or the
all-False assignment**. On these graphs the decoder's votes come out as the all-True assignment, and the verifier also
tries its complement, the all-False assignment. In a second search restricted to satisfiable formulas that neither
constant assignment satisfies, the chain decided **0 of 75**. This is what
the structure of the chain's graph predicts: at the parameters that fit in memory the graph is the same for every formula
(disjoint copies of one 18-vertex graph), so Salvador's optimal cover cannot carry a formula-specific assignment. The
`c decided by:` line says which assignment the verifier accepted and whether a constant assignment also satisfies the
formula, so that a decision by the chain is never mistaken for more than it is.

## Why SatyPy Cannot Decide 3SAT through the Gap Reduction

The gap reduction decides satisfiability only at the parameters for which the reference proves its soundness: the latent
alphabet gadget of its Lemma 3.1, a repetition exponent `t ≥ 10,240,000 · ln 2 ≈ 7,097,828` (its Section 7.2), and a
long sequence construction. The repeated game alone then has at least `4^7,097,828` edges (a number with about 4.3
million digits) for a single clause, which no computer can store. At the parameters that fit in memory the reduction
loses its gap: the clause-to-parity gadget keeps it (7/10 against at most 7/10 − 1/(5m)), the rank-one matrix test
with a two-letter alphabet gives every assignment the same value 3/4, and the sequence construction with `h = 1` makes
the game trivially satisfiable. The resulting graph is a disjoint union of copies of one 18-vertex graph with minimum
cover 12, for every formula. Every known reduction from 3SAT to Vertex Cover with a constant gap goes through the PCP
theorem and has astronomically large constants, and a proof that Salvador achieves a ratio below 2 on the gap instances
would itself imply P = NP. SatyPy therefore implements the chain faithfully, uses it with a guarded gap rule and a
verified decoder, and reports honestly when it cannot decide.

## References

- OpenAI Math Team, *The Unique Games Conjecture and Optimal Approximation Thresholds* (Result Family 102), GitHub
  repository [openai/math](https://github.com/openai/math/blob/main/lean/docs/102.md), October 2026.
- S. Khot and O. Regev, *Vertex cover might be hard to approximate to within 2 − ε*, J. Comput. System Sci. 74 (2008)
  335–349.
- R. M. Karp, *Reducibility among combinatorial problems*, 1972; M. R. Garey and D. S. Johnson, *Computers and
  Intractability*, Freeman, 1979.
- B. Aspvall, M. F. Plass and R. E. Tarjan, *A linear-time algorithm for testing the truth of certain quantified
  Boolean formulas*, Inform. Process. Lett. 8 (1979) 121–123.
- F. Vega, [Salvador 0.1.0](https://pypi.org/project/salvador/).

## Implementation

- **Programming Language:** Python
- **Author:** Frank Vega

## License

This code is released under the MIT License.

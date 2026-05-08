# Final Exam
**CMSC 27200**
_March, 2022_

**Important notes:**
- 24 hours from download to submission. Extra-time accommodations with the University are honored to the letter (please remind us, but you may submit the ordinary way on Gradescope).

In any case, the exam should be submitted not later than midday Saturday (11:59a). Exceptions in limited circumstances only; must be cleared in advance.
- Open book/notes, no collaboration, no web consultation (besides class resources), no asking Ed Q's except private clarification or logistics questions to staff. Afterwards, no discussing with students who have not yet taken the exam.
- There are 5 problems, but you are to choose only one of Problems 4 and 5 to complete. So a completed exam will do \{P1, P2, P3\} and one of P4 or P5. If you submit partial work on each of P4, P5, you must clearly indicate which one you want graded.
- It's good to look over all the problem statements first. Read carefully.
- Show your work. Answers without justification will be given little credit.


---

# Problem 1 (25 points). (Stores and social value)

On a long stretch of semi-rural residential road, there are many houses but no stores to provide local service. Locals want access to Bookstores, Drugstores, and Grocery stores ($B,D,G$). New zoning laws allow for stores to be constructed at $n$ evenly-spaced positions $1,2,\ldots,n$.

Each position $i \in [n]$ receives applications from a nonempty subset $S_i$ of the business types. E.g. if $S_i = \{B,D\}$ then a bookstore and drugstore have each applied to open at position $i$.

We can choose one and only one of the applications to fulfill at each location. (Each application comes from a separate entrepreneur, so we can make independent choices per location.) An assignment is a function $F$ which chooses a single element $s_i$ of $\{B,D,G\}$, for each $i$, and we say $F$ is feasible if $s_i \in S_i$ for each $i$.

We consider the population to be evenly distributed across the $n$ locations. A resident at position $i$ is said to have easy access to the stores at positions $\{i-1,i,i+1\}$, except for the boundary cases: $i=1$ residents have easy access to locations $\{1,2\}$ and $i=n$ have easy access to $\{n-1,n\}$.

The social value of an assignment $F$ is defined as a sum of its social value for the residents at locations $i$, for $i=1,\ldots,n$. The social value for residents at $i$ is defined as the number of distinct store types they have easy access to.

Give an algorithm which, on input describing $S_1,\ldots,S_n$, computes the maximum social value of any feasible assignment $F$. (You don't have to output an assignment, just the optimal value.) The running time should be bounded by a polynomial function of $n$. Prove correctness and efficiency. (You need not minimize the runtime or give the best-possible runtime bound for your algo, as long as you prove a poly-time upper bound.)

Example: if $n=4$ and
\[
S_1=\{B,G\}, \qquad S_2=\{B,D\}, \qquad S_3=\{B,D,G\}, \qquad S_4=\{B,G\}
\]
then the assignment
\[
F=(s_1,s_2,s_3,s_4)=(B,D,G,B)
\]
is feasible and has social value $2+3+3+2$, which is clearly best-possible, since residents at each position have easy access to distinct store types at each position within their range. (Note that this may not be possible in general, in which case you should output the largest social value obtained by a feasible assignment.)

**Solution 1.** Write your solution to Problem 1 here. Expand this area as needed.


---

# Problem 2 (25 points). (Saturated edges)

For both parts below we are given a directed graph $G=(V,E)$ with distinguished source vertex $s$, sink vertex $t$, integer edge capacities $c_e>0$ for each $e\in E$, and a flow $f=\{f(e)\}$ defined on edges. An edge is called saturated if $f(e)=c_e$.

- We say that the flow $f$ is a blocking flow if for every directed path from $s$ to $t$ there is a saturated edge somewhere along the path. Does it follow that $f$ is a maximum $s-t$ flow? Prove or give a counterexample.

- If $f$ is a maximum $s-t$ flow, consider the set $T$ of saturated edges. Is the total capacity of $T$ equal to the minimum total directed capacity of any $s$-$t$ cut? Prove or give a counterexample.

**Solution 2.** Write your solution to Problem 2 here. Expand this area as needed.


---

# Problem 3 (25 points). (Disconnecting graphs)

Consider the following problem, Disconnection:

**Input:** an undirected, connected graph $G$.

**Output:** the minimum value $k$ such that there exist $k$ edges whose removal disconnects the graph into two or more connected components.

Give an algorithm for this problem whose runtime is bounded by a polynomial in $n=|V(G)|$, the number of vertices. Prove correctness and efficiency.

Observe: There are no source/sink nodes in the problem statement. Also, the input graph is undirected and unweighted. Keep this in mind and supply details if/when applying algorithms developed for other types of graphs.

**Solution 3.** Write your solution to Problem 3 here. Expand this area as needed.


---

**DO THIS PROBLEM OR PROBLEM 5, BUT NOT BOTH**

# Problem 4 (25 points). (3-SAT with restricted variable occurrences)

Prove that the following special case of the 3-SAT (3-CNF satisfiability) problem, which we'll call 3-SAT(4), is NP-complete.

**Input:** a collection of clauses $C_1,\ldots,C_m$ over Boolean variables $x_1,\ldots,x_n$, where each clause $C_j$ is an OR of at most 3 variables or negated variables,\footnote{Recall: $\lor$ is “inclusive” OR, i.e. $1\lor 1=1\lor 0=0\lor 1=1$. Also, $\land$ is AND.} e.g.
\[
(x_1\lor x_3\lor x_7), \qquad (x_2\lor x_4), \quad \text{etc.}
\]
and, such that each variable $x_i$ appears in at most 4 of the clauses $C_j$.

(Here we include negated appearances in this count, e.g. if $x_1$ appears twice positively then it can appear only twice in negated form.)

These clauses represent the CNF (conjunctive normal form) formula
\[
F=\bigwedge_j C_j.
\]

**Decide:** is there an assignment to the variables that simultaneously satisfies every clause $C_j$? Equivalently, is there an assignment that satisfies $F$?

Hint: at least one of the following known NP-complete problems is a good choice to make use of in your proof: 3-SAT, Hamiltonian Cycle in undirected graphs, 3-Coloring. (The other two may be less convenient, so choose carefully.)

Example: $F=(x_1\lor x_3\lor x_4)\land (x_2\lor x_4)\land (x_3\lor x_4)$ is a CNF formula in which each clause $C_1,C_2,C_3$ is of width at most 3, and each variable appears at most 4 times.

In fact each variable appears at most 3 times, but that's certainly allowed by the problem. This is a YES instance of 3-SAT(4), since $F$ is satisfied by e.g. the assignment $(y_1,y_2,y_3,y_4)=(0,1,0,1)$.

**Solution 4.** Write your solution to Problem 4 here. Expand this area as needed.


---

**DO THIS PROBLEM OR PROBLEM 4, BUT NOT BOTH**

# Problem 5 (25 points). (Banquets)

Sometime in the not-too-distant future, friends gather for a banquet-style dinner at a large restaurant. There are $n$ people and $n$ dishes. (Again: we expect the same number of people and dishes! Important!!)

Every participant only likes certain dishes. We consider a decision problem in which we wish to know if we can seat the $n$ people around a circular table with a dish between every pair of participants, so that every participant likes both dishes placed at their sides.

**Input:** An $n\times n$ binary matrix $M$ such that $M_{i,j}=1$ if person $i$ likes dish $j$ and $M_{i,j}=0$ otherwise.

**Decide:** Whether there is an arrangement of all the people and dishes around a circular table, with a dish between any two adjacent people, such that every person likes both dishes placed at their two sides.

Note: every dish comes in a single plate and can be only placed in a single position.

Show that this decision problem, Banquets, is NP-complete. (The banquet is still a success.)

Hint: at least one of the following known NP-complete problems is a good choice to make use of in your proof: 3-SAT, Hamiltonian Cycle in undirected graphs, 3-Coloring. (The other two may be less convenient, so choose carefully.)

**Solution 5.** Write your solution to Problem 5 here. Expand this area as needed.

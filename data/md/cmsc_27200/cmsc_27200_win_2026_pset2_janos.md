# Problem Set 2
**CMSC 27200: Theory of Algorithms**
_Assigned January 14, 2026, Due January 20, 2026_

# Problem 0: Collaborators and Outside Sources
Who did you collaborate with?<br>
<br>
Did you use any outside sources? If so, which sources did you use?
# Problem 1: Dijkstra's Algorithm (25 points)
Use Dijkstra's algorithm to find the shortest path(s) from $s$ to $t$ in the following graph $G$.
```latex
    \begin{tikzpicture}[
      mycircle/.style={
         circle,
         draw=black,
         fill=white,
         fill opacity = 0.3,
         text opacity=1,
         inner sep=0pt,
         minimum size=20pt,
         font=\small},
      myarrow/.style={-Stealth},
      node distance=0.6cm and 1.2cm
      ]
      \node[mycircle]  at (-3, 0) (s) {$s$};
      \node[mycircle]  at (-1, 2) (a) {$a$};
      \node[mycircle]  at (1, 2) (b) {$b$};
      \node[mycircle]  at (-1, 0) (c) {$c$};
      \node[mycircle]  at (1, 0) (d) {$d$};
      \node[mycircle]  at (-1, -2) (e) {$e$};
      \node[mycircle]  at (1, -2) (f) {$f$};
      \node[mycircle]  at (3, 0) (t) {$t$};

    \foreach \i/\j/\txt/\p/\pp in {% start node/end node/text/position
      s.45/a.225/10/above/0.5,
      s.00/c.180/11/above/0.5,
      s.315/e.135/3/above/0.5,
      c.90/a.270/2/right/0.5,
      c.270/e.90/1/right/0.5,
      a.00/b.180/4/above/0.5,
      c.00/d.180/7/above/0.5,
      e.00/f.180/3/above/0.5,
      b.225/c.45/2/above/0.5,
      f.135/c.315/2/above/0.5,
      b.270/d.90/3/right/0.5,
      f.90/d.270/11/right/0.5,
      b.315/t.135/2/above/0.5,
      d.00/t.180/2/above/0.5,
      f.45/t.225/10/above/0.5
      }
       \draw [myarrow] (\i) -- node[font=\small,\p,pos=\pp] {\txt} (\j);

    \end{tikzpicture}
```

For your answer, first give the state of the priority queue after we add in the edges going out from $s$. Then give the following data for each new vertex that is reached.
- The name of the vertex $v$ which is reached and the length of the shortest path from $s$ to $v$.
- The state of the priority queue after we add in the edges which go out from $v$.

After giving this data, find **all of the shortest paths** from $s$ to $t$.<br>
<br>
Note: For this problem, you do not need to show the heap structure of the priority queue. Instead, you can represent the priority queue as a sorted list. Also, you may use either a priority queue with edges or a priority queue with vertices (where the value for a vertex decreases when a shorter path to that vertex is found).
# Problem 2: Guarding the Vault (25 points)
You are in charge of guarding a vault. You would like to take a vacation from time $0$ to time $T$, but first you need to hire other guards to guard the vault while you are away (it is okay if more than one person is guarding the vault, but the vault must be guarded at all times). You know $n$ guards you could call, each of whom has a set time interval $[a_i,b_i]$ when they can come and guard the vault. For all $t \in [0,T]$, there is at least one $i$ such that $t \in [a_i,b_i]$. Each guard charges the same amount regardless of the length of their interval $[a_i,b_i]$, so you would like to hire as few guards as possible.

Give a polynomial time greedy algorithm to minimize the number of guards that you need to hire, prove that your algorithm is correct, and analyze its runtime.<br>
<br>
Note: We can state this problem mathematically as follows. Find a set $I \subseteq [n]$ such that $[0,T] \subseteq \cup_{i \in I}{[a_i,b_i]}$ and $|I|$ is minimized.

# Problem 3: Maximum Cardinality Matching in a Rooted Tree (20 points, 5 points extra credit available)

Given an (undirected) graph $G=(V,E)$, a matching $S$ is a set of edges such that no two edges of $S$ have a common endpoint. A maximum cardinality matching is a matching $M$ with the maximum number of edges in it (i.e., for all matchings $S$, one has $|S| \leq |M|$).

  - (a) 10 points: Give a polynomial time greedy algorithm that finds a maximum cardinality matching in an (undirected) rooted tree $T = (V,E)$. You need to show that your algorithm runs in polynomial time and justify its correctness.

    Note: In this part of the problem, you are allowed to use “abstract” operations, such as “removing an edge from the graph”, “finding a node in the graph that satisfies some required properties”, without having to specify how to implement such operations (in fact, the implementations depend on how the tree $T$ is represented, which we deliberately not specify in this part of the problem). However, you should specify what these operations do and argue that they can be implemented in polynomial time.

  - (b) 10 points: Suppose the input rooted tree $T = (V,E)$ in part (a) is given by the adjacency lists of its vertices. Specifically, its vertices are $V = \{1, \cdots, n\}$, and for each node $v \in V$, its children are given as an array $\mathsf{child}(v)$. Show how to implement your greedy algorithm from part (a). You need to specify the data structure that you use in your implementation, and analyze the runtime of your implementation of the algorithm.

  - (c) 5 points extra credit: Give an algorithm (together with its implementation using a data structure) for part (b) whose runtime is optimal, i.e., the best possible up to a constant factor. You should analyze the runtime of your implementation and justify why this is optimal.

    Note: you are allowed to use the same algorithm and implementation from part (b), and if you do so, you don't need to analyze its runtime again.

# Problem 4: Denominations of Currencies (20 points)

- (a) 10 points: A bank ATM machine has (sufficiently many) bills in the denominations
\$1, \$5, \$10, \$20, \$50. Design a polynomial time greedy algorithm that, given a request for providing \$$N$ of cash, satisfies the request by
providing a list of the number of bills of each currency, such that the total number of bills is minimum.

For example, if $N=87$,
the correct answer should be: 1 \$50 bill, 1 \$20 bill, 1 \$10 bill, 1 \$5 bill and 3 \$1 bill.
You should  prove that your algorithm is correct.

- (b) 5 points: Suppose that in a different country, the available denominations were 1, 5, and 7 units of currency. Show that the greedy algorithm in part (a) is not optimal.

- (c) 5 points: Suppose that the country in part (b) ran out of bills for 1 unit of currency, so the only available denominations are 5 and 7 units of currency. Clearly, with those bills you will not be able to do payments of 1, or 2, or 8. Prove that you will be able to make payments for every sufficiently large natural number $n$. (More precisely, show that
there exists $n_0 > 0$ such that for every $n \geq n_0$, there are natural numbers $u,v$ such that $n=5u+7v$).


---
# Conversion Note
This file uses the provided starter TeX for the original problem statements and TikZ graph relationships, then includes the full solution text extracted from the matching PDF. The graph drawings do not need to be pixel-identical to the PDF; the directed edges and weights are preserved in the starter TeX where provided.


---
# Full Solution Text Extracted from PDF
```text
                                      Problem Set 2
                           CMSC 27200: Theory of Algorithms
                   Assigned January 14, 2026, Due January 20, 2026


Problem 1: Dijkstra's Algorithm (25 points)
Use Dijkstra's algorithm to find the shortest path(s) from s to t in the following graph G.

                                                    4
                                            a            b
                                     10             2             2
                                                2            3
                                     11             7             2
                                s           c           d              t
                                      3             2             10
                                                1            11
                                                    3
                                            e           f

For your answer, first give the state of the priority queue after we add in the edges going out from
s. Then give the following data for each new vertex that is reached.

   1. The name of the vertex v which is reached and the length of the shortest path from s to v.

   2. The state of the priority queue after we add in the edges which go out from v.

After giving this data, find all of the shortest paths from s to t.


    Note: For this problem, you do not need to show the heap structure of the priority queue.
Instead, you can represent the priority queue as a sorted list. Also, you may use either a priority
queue with edges or a priority queue with vertices (where the value for a vertex decreases when a
shorter path to that vertex is found).

Problem 1 Solution
Applying Dijkstra's algorithm with a priority queue containing vertices and reducing the distance
to a vertex when a shorter path is found:

--- page break ---
                    Vertex name Vertex distance       Priority queue state
                         s             0             (e, 3), (c, 11), (a, 10)
                         e             3             (f, 6), (c, 11), (a, 10)
                         f             6        (c, 8), (a, 10), (d, 17), (t, 16)
                         c             8            (a, 10), (d, 15), (t, 16)
                         a            10            (b, 14), (d, 15), (t, 16)
                         b            14                 (d, 15), (t, 16)
                         d            15                      (t, 16)
                         t            16

    Applying Dijkstra's algorithm with a priority queue containing edges:

   Vertex name Vertex distance                       Priority queue state
        s             0                          (s9e, 3), (s9c, 11), (s9a, 10)
        e             3                          (e9f, 6), (s9c, 11), (s9a, 10)
        f             6             (f 9c, 10), (s9c, 11), (s9a, 10), (f 9d, 17), (f 9t, 16)
        c             8             (c9d, 15), (c9a, 10), (s9a, 10), (f 9d, 17), (f 9t, 16)
        a            10                   (a9b, 14), (f 9d, 19), (c9d, 19), (f 9t, 20)
        b            14        (f 9d, 19), (c9d, 19), (f 9t, 20), (b9c, 16), (b9t, 16), (b9d, 17)
        d            15              (f 9t, 20), (b9c, 16), (b9t, 16), (b9d, 17), (d9t, 16)
        t            16                    (b9c, 16), (b9t, 20), (b9d, 17), (d9t, 16)

    There are two shortest paths of length 16: s9e9f 9t and s9e9f 9c9a9b9t.


Problem 2: Guarding the Vault (25 points)
You are in charge of guarding a vault. You would like to take a vacation from time 0 to time T , but
first you need to hire other guards to guard the vault while you are away (it is okay if more than
one person is guarding the vault, but the vault must be guarded at all times). You know n guards
you could call, each of whom has a set time interval [ai , bi ] when they can come and guard the
vault. For all t ? [0, T ], there is at least one i such that t ? [ai , bi ]. Each guard charges the same
amount regardless of the length of their interval [ai , bi ], so you would like to hire as few guards as
possible.
     Give a polynomial time greedy algorithm to minimize the number of guards that you need to
hire, prove that your algorithm is correct, and analyze its runtime.

Note: We can state this problem mathematically as follows. Find a set I ? [n] such that [0, T ] ?
?i?I [ai , bi ] and |I| is minimized.

Problem 2 Solution
Without loss of generality, we can perturb the intervals (by replacing [ai , bi ] with [ai - e, bi + e]) so
that all intervals endpoints are distinct without changing the validity of any schedules.


                                                    2

--- page break ---
    We pick intervals [ai1 , bi1 ], [ai2 , bi2 , . . . , aik , bik ] one at a time using a greedy strategy: if the last
interval we chose was Iij := [aij , bij ], we choose the interval Iij+1 to be the interval containing bij
with the latest end time (or at the very first step, the interval containing 0 with the latest end time).
    We can prove the optimality of this algorithm by contradiction. Let S be the schedule produced
by our greedy algorithm and S ? any other schedule. Let f (S, t) (resp. f (S ? , t)) be the number of
intervals in S (resp. S ? ) which end at or before t. Let b be the smallest value such that f (S, b) >
f (S ? , b). By minimality of b, there is an interval Ij := [aij , bij ] =: [a, b] in S. Because f (S, t) =
f (S ? , t) for all t < b, the set of intervals in S and S ? ending strictly before b must be the same.
Sorting the intervals in S by their end time, let Ij-1 := [aij-1 , bij-1 ] be the interval in S immediately
preceding [a, b]. Because S ? is also a schedule, there is an interval [a? , b? ] in S ? containing bij-1 , but
because f (S, b) > f (S ? , b), we must have a? < bij-1 < b < b? . This is a contradiction, because
after choosing Ij-1 , the greedy algorithm would have chosen [a? , b? ] over [a, b] since both contain
bij-1 but b? > b.
    We can implement this algorithm by sorting the list of intervals by their ending time and, after
choosing Ij := [aij , bij ], picking Ij+1 to be the interval with the latest end time containing bij . The
total number of intervals we choose in this way is at most O(n) and we take O(n) time to find Ij+1
given Ij since we may need to search through the whole list, so this gives an algorithm running in
O(n2 ) time.
    We can improve this to O(n log n) if we can (after at most O(n log n) precomputation), find
the latest-ending interval containing bji in O(log n) time. Data structures designed for such queries
are interval and range trees - variants of binary search trees - and either would work here. Here is
a more down-to-earth approach. Let (tj )2n          j=1 be a list containing all interval start and end times. It
suffices to be able to compute, for each tj , the intervals containing tj sorted by ending time. For
this, let Lj-1 be a binary search tree containing the intervals containing tj-1 ordered by ending
time. If tj is an interval start (resp. end) point, we insert (resp. remove) interval Ij into (resp.
from) Lj-1 to obtain Lj . Both insertion and deletion from a binary search tree take O(log n) time,
and we process each interval exactly twice, so computing the BSTs {Lj }2n                  j=1 takes O(n log n) time.
With these precomputations in hand, we can execute the greedy algorithm in O(n log n) time.
    We cannot hope to execute this greedy algorithm in better than O(n log n) time since already
at the first step we need to sort the intervals by end time.


Problem 3: Maximum Cardinality Matching in a Rooted Tree
(20 points, 5 points extra credit available)
Given an (undirected) graph G = (V, E), a matching S is a set of edges such that no two edges of
S have a common endpoint. A maximum cardinality matching is a matching M with the maximum
number of edges in it (i.e., for all matchings S, one has |S| <= |M |).
  (a) 10 points: Give a polynomial time greedy algorithm that finds a maximum cardinality match-
      ing in an (undirected) rooted tree T = (V, E). You need to show that your algorithm runs in
      polynomial time and justify its correctness.
       Note: In this part of the problem, you are allowed to use "abstract" operations, such as "re-
       moving an edge from the graph", "finding a node in the graph that satisfies some required

                                                          3

--- page break ---
      properties", without having to specify how to implement such operations (in fact, the imple-
      mentations depend on how the tree T is represented, which we deliberately not specify in
      this part of the problem). However, you should specify what these operations do and argue
      that they can be implemented in polynomial time.
 (b) 10 points: Suppose the input rooted tree T = (V, E) in part (a) is given by the adjacency
     lists of its vertices. Specifically, its vertices are V = {1, ? ? ? , n}, and for each node v ? V ,
     its children are given as an array child(v). Show how to implement your greedy algorithm
     from part (a). You need to specify the data structure that you use in your implementation,
     and analyze the runtime of your implementation of the algorithm.
  (c) 5 points extra credit: Give an algorithm (together with its implementation using a data struc-
      ture) for part (b) whose runtime is optimal, i.e., the best possible up to a constant factor. You
      should analyze the runtime of your implementation and justify why this is optimal.
      Note: you are allowed to use the same algorithm and implementation from part (b), and if
      you do so, you don't need to analyze its runtime again.

Problem 3 Solution
We start with a preliminary lemma. Given a rooted tree T , let f (T ) denote the maximum cardinal-
ity of a matchings in T .
Lemma 0.1. Let T be a rooted tree with root r and {Ti } the set of subtrees rooted at the children
of r. Then                  X                           X
                                 f (Ti ) <= f (T ) <= 1 +    f (Ti )
                                  i                          i

Proof. The lower bound is because a matching on all the subtrees separately gives a matching on
T . The upper bound is because any matching contains at most one edge containing r, and having
chosen such an edge, all the other edges must give a matching on the {Ti }.
   We abbreviate "maximal cardinality    Pmatching" as MCM. It follows from the lemma that the
cardinality of an MCM on T is 1 + i f (Ti ) if and only if any MCM must include an edge
containing r - if an MCM does not hit r, then the MCM gives an MCM on ?i Ti , and if the
cardinality of an MCM on T exceeds that of ?i Ti then it had better make use of some edges not
contained in T , i.e. the edges containing r.

  (a) Our algorithm A to compute an MCM on T runs as follows. If T is a single vertex, A(T )
      returns the empty set. Otherwise, A(T ) returns ?i A(Ti ), as well as (r, rj ) where j is the
      smallest i such that ri , the root of Ti , is not contained in the matching produced by A(Ti ),
      if such an i exists. We claim that A(T ) produces an MCM. Furthermore, we claim that this
      MCM  P includes an edge containing the root r if and only if the cardinality of the MCM is
      1 + i f (Ti ). Observe that this happens if and only ifP   any MCM includes a edge containing
      r (as an MCM avoiding r cannot have size exceeding i f (Ti )). Intuitively, this means that
      the MCM only includes an edge containing r if it absolutely needs to.
      We prove this claim by induction on the height of the tree. The base case of a single vertex
      is immediate since the MCM is empty. Otherwise, applying the inductive hypothesis to the

                                                  4

--- page break ---
     subtrees {Ti }, we can produce an MCM of ?i Ti . We are able to include an additional edge
     (attaniing the upper bound of the lemma) if and only if there is an MCM on some Ti which
     does not include its root ri . By the inductive hypothesis, the MCMs produced by P A(Ti ) will
     avoid the root ri if possible. If we can avoid it for some Ti , then f (T ) = 1 + i f (Ti ) and
     our algorithm produces a matching including the edge (r, ri ). Otherwise, A returns ?A(Ti ),
     which does not include any edge containing r. In either case, we have optimality by the
     lemma.
     We start at each leaf and work our way up. The processing at each vertex involves looking
     through the children of the vertex and seeing if any of its children subtrees have MCMs that
     do not include the subtree root.

 (b) We use the given adjacency list representation of the graph, but a each vertex v, we also store
     the parent of v and an edge from v to one of its children if the MCM on the subtree rooted at v
     includes such Traversing the tree "bottom up", starting from the leaves, and applying A, we
     can update these extra fields as we make our way up the tree as defined in the previous part.
     Given the data of this boolean for every vertex in the tree, we can reconstruct the matching
     istself. We process each edge exactly once in this algorithm, so the runtime is O(m) = O(n).

 (c) The algorithm we give is O(m) = O(n). This is optimal as we need at least this long to read
     the input.


Problem 4: Denominations of Currencies (20 points)
 (a) 10 points: A bank ATM machine has (sufficiently many) bills in the denominations $1, $5,
     $10, $20, $50. Design a polynomial time greedy algorithm that, given a request for providing
     $N of cash, satisfies the request by providing a list of the number of bills of each currency,
     such that the total number of bills is minimum.
     For example, if N = 87, the correct answer should be: 1 $50 bill, 1 $20 bill, 1 $10 bill, 1 $5
     bill and 3 $1 bill. You should prove that your algorithm is correct.

 (b) 5 points: Suppose that in a different country, the available denominations were 1, 5, and 7
     units of currency. Show that the greedy algorithm in part (a) is not optimal.

 (c) 5 points: Suppose that the country in part (b) ran out of bills for 1 unit of currency, so the
     only available denominations are 5 and 7 units of currency. Clearly, with those bills you will
     not be able to do payments of 1, or 2, or 8. Prove that you will be able to make payments
     for every sufficiently large natural number n. (More precisely, show that there exists n0 > 0
     such that for every n >= n0 , there are natural numbers u, v such that n = 5u + 7v).

Problem 4 Solution
                                                 k
 (a) Given a target value N and bill values {aj
                                              i }i=1
                                                   k where a1 = 1 and ai <j ai+1 , our
                                                                                     k greedy algo-
                                                 N                          N -nk ak
     rithm decomposes N by choosing nk := ak bills of value ak , then ak-1             bills of value

                                                 5

--- page break ---
    ak-1 , and so on. (Because a1 is 1, this algorithm is guaranteed to output a decomposition of
    N ). The greedy algorithmj produces
                                   k       the unique decomposition of N such that the bill with
                              ai+1
    value ai appears at most ai times.

    Lemma 0.2. The greedy algorithm is optimal (produces a decomposition using the fewer
    number of bills) whenever ai |ai+1 for all i <= k - 1.

    Proof. This follows from an exchange argument. In a decomposition where the ith bill is
    used at least ai+1
                   ai
                        times, we can replace ai+1
                                               ai
                                                   of them these bills with one bill of value ai+1 .
    This will improve the decomposition (i.e. reduce the total number of bills). Applying this
    procedure starting at i = 1 and working our way up to i = k, we end up with a decomposition
    where the ith bill is used at most ai+1
                                        ai
                                            times. This is exactly the decomposition produced by
    the greedy algorithm.

    Thus, the greedy algorithm gives optimal decompositions given the currency system (1, 5, 10, 20),
    and we need to check that adding 50 does not break optimality. Again we may apply an ex-
    change argument. If a decomposition has three 20s (i.e. if the decomposition has more 20s
    than in the greedy decomposition), we may improve the decomposition by replacing them
    with one 50 and one 10. Doing this repeatedly, we end up with the decomposition produced
    by the greedy algorithm.

    Remark 0.3. Since this is a mistake I (Abhijit) initially made, I want to remark that it is
    not true that the greedy algorithm works whenever 2ai <= ai+1 . For example, consider
    (ai )i = (1, 2, 4, 14, 35). Then, N = 42 = 35 + 4 + 2 + 1 = 3 ? 14, so the greedy algorithm
    is not optimal.

(b) Observe that 10 = 7 + 1 + 1 + 1 = 5 + 5. The greedy algorithm would choose the former
    decomposition, but this is not optimal.

(c) Observe that if for some m there is a representation m = 5u + 7v, then there is such a
    representation for any n > m for which n ? m mod 5. Observe that 7 ? 2 mod 5,
    14 ? 4 mod 5, 21 ? 1 mod 5, and 28 ? 3 mod 5, so to ensure that we've covered all
    the residue classes, it suffices to take (28, 29, 30, 31, 32). We can do better by starting with
    n0 = 24, so that way we cover 28 "just in time".


                                                6

--- page break ---
```

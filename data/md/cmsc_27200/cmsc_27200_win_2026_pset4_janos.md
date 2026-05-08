# Problem Set 4
**CMSC 27200: Theory of Algorithms**
_Assigned February 11, 2026, Due February 17, 2026_

# Problem 0: Collaborators and Outside Sources
Who did you collaborate with?<br>
<br>
Did you use any outside sources? If so, which sources did you use?
# Problem 1: Bellman-Ford (25 points)
- (a) 20 points: Simulate the execution of the Bellman-Ford algorithm on the graph below. For your answer, for each $k \in \{0,1,2,\ldots,10\}$ and each vertex $v \in V(G)$, you should provide the length of the shortest path from $s$ to $v$ which uses at most $k$ edges (as a table). You should also find the shortest path from $s$ to $t$ from your table.

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
      \node[mycircle]  at (1, 2) (d) {$d$};
      \node[mycircle]  at (-1, 0) (b) {$b$};
      \node[mycircle]  at (1, 0) (e) {$e$};
      \node[mycircle]  at (-1, -2) (c) {$c$};
      \node[mycircle]  at (1, -2) (f) {$f$};
      \node[mycircle]  at (3, 2) (g) {$g$};
      \node[mycircle]  at (3, 0) (h) {$h$};
      \node[mycircle]  at (5, 0) (t) {$t$};

    \foreach \i/\j/\txt/\p/\pp in {% start node/end node/text/position
      s.45/a.225/3/above/0.5,
      s.00/b.180/4/above/0.5,
      s.315/c.135/1/above/0.5,
      a.00/d.180/-3/above/0.5,
      a.330/h.150/5/above/0.5,
      b.45/d.225/1/above/0.25,
      b.90/a.270/-2/left/0.5,
      c.45/e.225/1/above/0.5,
      d.315/h.135/3/above/0.5,
      e.270/f.90/2/right/0.5,
      f.180/c.00/-5/above/0.5,
      g.180/d.00/-4/above/0.5,
      h.90/g.270/4/right/0.5,
      h.00/t.180/3/above/0.5
      }
       \draw [myarrow] (\i) -- node[font=\small,\p,pos=\pp] {\txt} (\j);

    \end{tikzpicture}
```

- (b) 5 points: For this graph, for which vertices $v \in V(G)$ does Bellman-Ford correctly compute the length of the shortest path from $s$ to $v$? What causes Bellman-Ford to fail for the other vertices? If we look at the 10th iteration, is there a warning sign for this failure?

# Problem 2: Music Festival (25 points)
You are attending a large music festival. At this festival, there are $k$ venues and $n$ time slots. If you are at venue $i$ during time slot $j$ then you will derive enjoyment $h_{ij}$ from the show there. Unfortunately, the venues are rather far apart, so while you can change venues during the festival, each time you move from one venue to another takes one time slot. Given this, what is the maximum total enjoyment you can have?

We can state this problem mathematically as follows: Given a $k \times n$ matrix $H$ where $h_{ij}$ is your enjoyment from being at venue $i$ during time slot $j$, find a schedule $S = ((i_1,j_i),\ldots,(i_l,j_l))$ such that
- $1 \leq j_1 < j_2 < \ldots < j_l \leq n$ (you can be at most one venue at any given time slot)
- For all $t \in [l-1]$, if $i_{t+1} \neq i_{t}$ then $j_{t+1} \geq j_{t} + 2$ (traveling between venues takes one time slot)
- $\sum_{t=1}^{l}{h_{{i_t}{j_t}}}$ is maximized.

Give a polynomial time algorithm to solve this problem, prove that your algorithm is correct, and analyze the runtime of your algorithm.

# Problem 3: Trading Stocks (25 points)
You are looking at a given stock over $n$ consecutive days, where the price for day $i \in \{1, \cdots, n\}$ is $p_i$ per share (assume for simplicity that the price is fixed during each day). You would like
to know: how should you choose a day $i$ on which to buy the stock and a
later day $j > i$ on which to sell it, so that the profit per share, $p_j - p_i$, is maximized?

You may assume for simplicity that $p_1 < p_2$, so that you can always make money.
Give an algorithm to find the optimal numbers $i$ and $j$ in $O(n)$ time.
You need to show that your algorithm is correct, and analyze its runtime.

# Problem 4: Unhidden Points (25 points)

You are given $n$ points $\{(x_i, y_i)\}_{i \in [n]}$ on the plane. Assume for simplicity that the coordinates $x_1, \cdots, x_n$ and $y_1, \cdots, y_n$ are all distinct.
We say that point $j$ *hides* point $i$ if $x_i < x_j$ and $y_i < y_j$, i.e., both coordinates of point $j$ are larger than point $i$.

Give an $O(n \log n)$ time algorithm to find the set of points that are not hidden by any other points. In other words, find the set $S = \{i: \text{For all } j \in [n] \setminus \{i\}, x_i > x_j \text{ or } y_i > y_j\}$. Explain why your algorithm is correct and takes $O(n \log n)$ time.<br>
<br>
Hint: What algorithmic paradigm do you want to use for this problem? If $i_1,\ldots,i_m$ are the unhidden points and $x_{i_1} < \ldots < x_{i_m}$, what can we say about $y_{i_1},\ldots,y_{i_m}$?<br>


---
# Conversion Note
This file uses the provided starter TeX for the original problem statements and TikZ graph relationships, then includes the full solution text extracted from the matching PDF. The graph drawings do not need to be pixel-identical to the PDF; the directed edges and weights are preserved in the starter TeX where provided.


---
# Full Solution Text Extracted from PDF
```text
                                       Problem Set 4
                          CMSC 27200: Theory of Algorithms


Problem 1: Bellman-Ford (25 points)
 (a) 20 points: Simulate the execution of the Bellman-Ford algorithm on the graph below. For
     your answer, for each k ? {0, 1, 2, . . . , 10} and each vertex v ? V (G), you should provide
     the length of the shortest path from s to v which uses at most k edges (as a table). You should
     also find the shortest path from s to t from your table.

                                                    -3                 -4
                                            a                 d                 g

                                   3                          5        3
                                       -2       1                                   4
                                   4                                                     3
                           s                b                 e                 h            t
                                   1                1
                                                                  2
                                                    -5
                                            c                f


     Solution:

                          k    s       a    b       c        d        e     f       g    h   t
                          0    0       ?    ?       ?        ?        ?     ?       ?    ?   ?
                          1    0       3    4       1        ?        ?     ?       ?    ?   ?
                          2    0       2    4       1        0        2     ?       ?    8   ?
                          3    0       2    4       1        -1       2     4       12   3   11
                          4    0       2    4       -1       -1       2     4       7    2   6
                          5    0       2    4       -1       -1       0     4       6    2   5
                          6    0       2    4       -1       -1       0     2       6    2   5
                          7    0       2    4       -3       -1       0     2       6    2   5
                          8    0       2    4       -3       -1       -2    2       6    2   5
                          9    0       2    4       -3       -1       -2    0       6    2   5
                          10   0       2    4       -5       -1       -2    0       6    2   5

     Shortest path from s to t: s -> b -> a -> d -> h -> t


                                                         1

--- page break ---
  (b) 5 points: For this graph, for which vertices v ? V (G) does Bellman-Ford correctly compute
      the length of the shortest path from s to v? What causes Bellman-Ford to fail for the other
      vertices? If we look at the 10th iteration, is there a warning sign for this failure?
      Solution: Bellman-Ford correctly computes the length of the shortest path from s to a, b, d,
      g, h and t. Bellman-Ford fails on vertices c, e and f because they lie on a negative cycle
      with weight 1 + 2 - 5 = -2. The warning sign is that a value is updated in the 10th iteration
      despite the fact that the longest path can use maximum n - 1 edges (or n vertices).


Problem 2: Music Festival (25 points)
You are attending a large music festival. At this festival, there are k venues and n time slots. If you
are at venue i during time slot j then you will derive enjoyment hij from the show there. Unfor-
tunately, the venues are rather far apart, so while you can change venues during the festival, each
time you move from one venue to another takes one time slot. Given this, what is the maximum
total enjoyment you can have?
    We can state this problem mathematically as follows: Given a k xn matrix H where hij is your
enjoyment from being at venue i during time slot j, find a schedule S = ((i1 , ji ), . . . , (in , jn )) such
that

   1. 1 <= j1 < j2 < . . . < jl <= n (you can be at most one venue at any given time slot)

   2. For all t ? [n - 1], if it+1 ?= it then jt+1 >= jt + 2 (traveling between venues takes one time
      slot)
      Pn
   3.    t=1 hit jt is maximized.

Give a polynomial time algorithm to solve this problem, prove that your algorithm is correct, and
analyze the runtime of your algorithm.
Solution: DP [i, j] = maximum enjoyment achievable at venue i by the end of time slot j

Algorithm 1 Maximum Total Enjoyment at a Music Festival
Input: k x n matrix H
 1: for i = 1, . . . , k do
 2:     DP [i, 1] <- hi1
 3: end for
 4: for j = 1, . . . , n do
 5:     for i = 1, . . . , k do         (
                                         DP [i, j - 1],         if i? = i
 6:        DP [i, j] <- hij + maxi? ?[k]
                                         DP [i? , j - 2],       otherwise
 7:     end for
 8: end for
 9: return maxi?[k] (DP [i, n])


                                                     2

--- page break ---
Correctness:
      Base case: At time slot 1, DP [i, 1] = hi1 for all i ? [k], so algorithm 1 returns maxi?[k] (DP [i, 1]) =
      maxi?[k] (hi1 ).
      Recursive step: The maximum enjoyment achievable at venue i by the end of time slot j
      is the enjoyment derived from that show, hij , plus the maximum enjoyment derived from
      shows before j. This could be achieved either by staying at venue i with an enjoyment of
      DP [i, j - 1], or by traveling from a previous venue i? with an enjoyment of DP [i? , j - 2]
      because it takes an additional time slot to travel from i? to i.
Runtime: We have to compute kn entries of DP , and each computation considers k previous
entries, plus a final maximum over k. This gives a total runtime of O(k 2 n).


Problem 3: Trading Stocks (25 points)
You are looking at a given stock over n consecutive days, where the price for day i ? {1, ? ? ? , n}
is pi per share (assume for simplicity that the price is fixed during each day). You would like to
know: how should you choose a day i on which to buy the stock and a later day j > i on which to
sell it, so that the profit per share, pj - pi , is maximized?
    You may assume for simplicity that p1 < p2 , so that you can always make money. Give an
algorithm to find the optimal numbers i and j in O(n) time. You need to show that your algorithm
is correct, and analyze its runtime.
Solution:

Algorithm 2 Maximum Profit from Trading Stocks
Input: prices p1 , . . . , pn
Output: days buy and sell
 1: minP rice <- p1
 2: minDay <- 1
 3: maxP rof it <- p2 - p1
 4: buy <- 1
 5: sell <- 2
 6: for i = 3, . . . , n do
 7:     if pi - minP rice > maxP rof it then
 8:          maxP rof it <- pi - minP rice
 9:          buy <- minDay
10:          sell <- i
11:     end if
12:     if pi < minP rice then
13:          minP rice, minDay <- pi , i
14:     end if
15: end for
16: return (buy, sell)


                                                   3

--- page break ---
Correctness: At the beginning of the iteration corresponding to day i, the maxP rof it is the max-
imum profit achievable using days 1, . . . , i - 1 and minP rice is the minimum price among days
1, . . . , i - 1. Before the first iteration, the maximum profit is achievable by buying on day 1 and
selling on day 2 by the assumption, and minP rice is the price on day 1. On day i, maxP rof it is
either the maxP rof it from day i - 1 or the profit from buying on the day with minP rice and sell-
ing on day i, whichever is greater. Similarly, minP rice is either the minP rice from day i - 1 or
pi , whichever is lower. After the last iteration (corresponding to day n), buy and sell will represent
the days on which to trade in order to achieve maxP rof it, so algorithm 2 will find the optimal
days to buy and sell on.

Runtime: Each of the O(n) iterations takes O(1) time, for a total runtime of O(n).


Problem 4: Unhidden Points (25 points)
You are given n points {(xi , yi )}i?[n] on the plane. Assume for simplicity that the coordinates
x1 , ? ? ? , xn and y1 , ? ? ? , yn are all distinct. We say that point j hides point i if xi < xj and yi < yj ,
i.e., both coordinates of point j are larger than point i.
     Give an O(n log n) time algorithm to find the set of points that are not hidden by any other
points. In other words, find the set S = {i : For all j ? [n] \ {i}, xi > xj or yi > yj }. Explain
why your algorithm is correct and takes O(n log n) time.

Hint: What algorithmic paradigm do you want to use for this problem? If i1 , . . . , im are the
unhidden points and xi1 < . . . < xim , what can we say about yi1 , . . . , yim ?
Solution:

Algorithm 3 Maximum Set of Unhidden Points
Input: points {(xi , yi )}i?[n]
Output: set S
 1: Sort points by decreasing x
 2: add 1 to S
 3: Ymax <- y1
 4: for i = 2, . . . , n do
 5:     if yi > Ymax then
 6:          add i to S
 7:          Ymax <- yi
 8:     end if
 9: end for
10: return S


Correctness: At the beginning of the iteration corresponding to point i, Ymax is the maximum y
for any point with x > xi . Before the first iteration, the maximum y is trivially y1 . Up to point i, yi
is either greater or less than Ymax since all y values are distinct by assumption. If yi is greater than


                                                       4

--- page break ---
Ymax , xi < xj and yi > yj , so point i is not hidden by any of the points already considered. It also
cannot be hidden by any future points because it has a greater x than them. Thus, point i is added
to set S and Ymax is updated. If yi is less than Ymax , it is hidden by the point with y = Ymax and
x > xi , so it is not added to S. After the last iteration, all of the n points will have been considered,
and set S will contain only the unhidden points.

Runtime: Each of the O(n) iterations takes O(1) time and the sort takes O(n log n) time, for
a total runtime of O(n log n).


                                                    5

--- page break ---
```

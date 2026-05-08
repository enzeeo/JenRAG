# Problem Set 1
**CMSC 27200: Theory of Algorithms**

# Problem 1: Gale-Shapley and Stable Matchings (25 points, 5 extra credit points available)
- (a) 15 points: Given the following preference lists, run the Gale-Shapley algorithm with group $A$ making the offers to obtain a stable matching.

Group $A$'s preference lists (from most preferred to least preferred):
- $a_1$: $b_3$, $b_2$, $b_1$, $b_4$
- $a_2$: $b_1$, $b_4$, $b_3$, $b_2$
- $a_3$: $b_4$, $b_1$, $b_3$, $b_2$
- $a_4$: $b_1$, $b_4$, $b_2$, $b_3$

Group $B$'s preference lists (from most preferred to least preferred):
- $b_1$: $a_1$, $a_3$, $a_4$, $a_2$
- $b_2$: $a_3$, $a_4$, $a_2$, $a_1$
- $b_3$: $a_3$, $a_2$, $a_1$, $a_4$
- $b_4$: $a_1$, $a_4$, $a_3$, $a_2$

For your answer (and for your answer to part b as well), you should give the following data. At each step, give the offer that is made, whether or not this offer is accepted, and the resulting partial matching.

**Solution:**
- $a_1$ makes offer to $b_3$: accepted as $b_3$ is unmatched

Current partial matching: $(a_1,b_3)$
- $a_2$ makes offer to $b_1$: accepted as $b_1$ is unmatched

Current partial matching: $(a_1,b_3)$, $(a_2,b_1)$
- $a_3$ makes offer to $b_4$: accepted as $b_4$ is unmatched

Current partial matching: $(a_1,b_3)$, $(a_2,b_1)$, $(a_3,b_4)$
- $a_4$ makes offer to $b_1$: accepted as $b_1$ prefers $a_4$ to $a_2$

Current partial matching: $(a_1,b_3)$, $(a_3,b_4)$, $(a_4,b_1)$
- $a_2$ makes offer to $b_4$: rejected as $b_4$ prefers $a_3$ to $a_2$

Current partial matching: $(a_1,b_3)$, $(a_3,b_4)$, $(a_4,b_1)$
- $a_2$ makes offer to $b_3$: accepted as $b_3$ prefers $a_2$ to $a_1$

Current partial matching: $(a_3,b_4)$, $(a_4,b_1)$, $(a_2,b_3)$
- $a_1$ makes offer to $b_2$: accepted as $b_2$ is unmatched

Final matching: $(a_3,b_4)$, $(a_4,b_1)$, $(a_2,b_3)$, $(a_1,b_2)$

- (b) 10 points: Now run the Gale-Shapley algorithm with group $B$ making the offers to obtain another stable matching. Which people are happier in this new stable matching (compared to the stable matching found in part a)?

**Solution:**
- $b_1$ makes offer to $a_1$: accepted as $a_1$ is unmatched

Current partial matching: $(a_1,b_1)$
- $b_2$ makes offer to $a_3$: accepted as $a_3$ is unmatched

Current partial matching: $(a_1,b_1)$, $(a_3,b_2)$
- $b_3$ makes offer to $a_3$: accepted as $a_3$ prefers $b_3$ to $b_2$

Current partial matching: $(a_1,b_1)$, $(a_3,b_3)$
- $b_4$ makes offer to $a_1$: rejected as $a_1$ prefers $b_1$ to $b_4$

Current partial matching: $(a_1,b_1)$, $(a_3,b_3)$
- $b_4$ makes offer to $a_4$: accepted as $a_4$ is unmatched

Current partial matching: $(a_1,b_1)$, $(a_3,b_3)$, $(a_4,b_4)$
- $b_2$ makes offer to $a_4$: rejected as $a_4$ prefers $b_4$ to $b_2$

Current partial matching: $(a_1,b_1)$, $(a_3,b_3)$, $(a_4,b_4)$
- $b_2$ makes offer to $a_2$: accepted as $a_2$ is unmatched

Final matching: $(a_1,b_1)$, $(a_3,b_3)$, $(a_4,b_4)$, $(a_2,b_2)$

$b_1$, $b_2$, $b_3$, and $b_4$ are happier in the new stable matching as they are each matched with someone higher on their preference list.

- (c) 5 points extra credit: What other stable matching(s) are there, if any? Note: For full extra credit you should show that you have indeed found all of the possible stable matchings. <br>
Hint is available.

**Solution:** Let $S_i$ denote the set of possible matches for each $a_i$. We use the fact that when group $A$ makes offers, G-S gives the best possible matching for $A$, and when group $B$ makes offers, G-S gives the worst possible matching for $A$ (Theorem 1.9). Because the best and worst possible matchings are consecutive on $a_1$, $a_2$, and $a_4$'s preference lists, we have $S_1=\{b_2,b_1\}$, $S_2=\{b_3,b_2\}$, and $S_4=\{b_1,b_4\}$. For $a_3$, we know $\{b_4,b_3\}\subseteq S_3$, but we don't know yet if $b_1\in S_3$.

If we match $a_3$ with $b_4$, then by elimination, we must match $a_4$ with $b_1$, $a_2$ with $b_3$, and $a_1$ with $b_2$ (giving the G-S matching when group $A$ offers). Similarly, if we match $a_3$ with $b_3$, we get the G-S matching when group $B$ offers. Finally, if we match $a_3$ with $b_1$, we must match $a_1$ with $b_2$, $a_2$ with $b_3$, and $a_4$ with $b_4$. To see that $M=\{(a_1,b_2),(a_2,b_3),(a_3,b_1),(a_4,b_4)\}$ is a stable matching, we make the following observations:
- The only person who $a_1$ prefers to $b_2$ is $b_3$, but $b_3$ prefers $a_2$ to $a_1$. Thus, there are no unstable pairs involving $a_1$.
- While $a_2$ prefers $b_1$ and $b_4$ to $b_3$, $b_1$ prefers $a_3$ to $a_2$ and $b_4$ prefers $a_4$ to $a_2$. Thus, there are no unstable pairs involving $a_2$.
- The only person who $a_3$ prefers to $b_1$ is $b_4$, but $b_4$ prefers $a_4$ to $a_3$. Thus, there are no unstable pairs involving $a_3$.
- The only person who $a_4$ prefers to $b_4$ is $b_1$, but $b_1$ prefers $a_3$ to $a_4$. Thus, there are no unstable pairs involving $a_4$.

There were maximum 3 possibilities for $a_3$'s partner, and each resulted in a unique stable matching, so there are exactly 3 stable matchings. In conclusion, the only other stable matching is $\{(a_1,b_2),(a_2,b_3),(a_3,b_1),(a_4,b_4)\}$.

# Problem 2: Big O Notation (25 points)
- (a) 15 points: Given each of the following statements, what can we say about $T(n)$ using Big $O$ notation? You are asked to give the *best possible answers* using the concepts of $O(\cdot)$, $\Omega(\cdot)$, and $\Theta(\cdot)$. If the given statement is not sufficient to decide that $T(n)$ is $O(\cdot)$, $\Omega(\cdot)$, or $\Theta(\cdot)$ of another simple function, you should indicate this in your answer. All logarithms are base 2.
- $T(n) \leq 3n + 2n^2 - 15$.

**Solution:** $O(n^2)$ as $2n^2$ is the fastest-growing term. There is no lower bound given, so we cannot conclude $\Omega(\cdot)$ or $\Theta(\cdot)$.

- $T(n)=\dfrac{\sqrt{n}}{2}+7(\log n)^{10}$.

**Solution:** $\Theta(\sqrt{n})$ because $O(\sqrt{n})$ and $\Omega(\sqrt{n})$. To compare $\dfrac{\sqrt{n}}{2}$ and $7\log^{10} n$, we ignore constants and compare the log of each: $\log(\sqrt{n})=\log(n^{1/2})=\dfrac{1}{2}\log n$ and $\log(\log^{10} n)=10\log(\log n)$. Since $\log n$ grows faster than $\log(\log n)$, $\dfrac{\sqrt{n}}{2}$ is the fastest-growing term.

- $T(n) \geq 10n^4 + 3n(1.1)^n$.

**Solution:** $\Omega(n(1.1)^n)$ because $3n(1.1)^n$, as an exponential, is the fastest growing term. There is no upper bound given, so we cannot conclude $O(\cdot)$ or $\Theta(\cdot)$.

- $2^n \leq T(n) \leq 7n^{22}2^n$.

**Solution:** $O(n^{22}2^n)$ and $\Omega(2^n)$. Since the $O(\cdot)$ and $\Omega(\cdot)$ don't match, we cannot conclude $\Theta(\cdot)$.

- $T(n)=\begin{cases}
14-5n+\dfrac{n^2}{2} & \text{if } n \bmod 2=0,<br>
3n\log n+100n & \text{if } n \bmod 2=1.
\end{cases}

**Solution:** $O(n^2)$ and $\Omega(n\log n)$. The upper bound ($O(n^2)$) is determined by the fastest-growing case (even $n$), while the lower bound ($\Omega(n\log n)$) is determined by the slowest-growing case (odd $n$). Since the $O(\cdot)$ and $\Omega(\cdot)$ don't match, we cannot conclude $\Theta(\cdot)$ for $T(n)$ overall.

- (b) 10 points: Order the functions below in order of increasing asymptotic growth. If two functions have the same asymptotic growth, you should indicate this. All logarithms are base 2.<br>
$2^n, ~~ n, ~~ \log n, ~~ n^2, ~~ n\log n, ~~ n^{\log n}, ~~ 2^{2\log n}, ~~ 2^{2n}, ~~ n^2/{\log n}, ~~ n2^n, ~~ 2^{\log\log n}, ~~ 2^{\sqrt{\log n}}$<br>
Hint is available.

**Solution:**
\[
\log n = 2^{\log\log n} < 2^{\sqrt{\log n}} < n < n\log n < \frac{n^2}{\log n} < 2^{2\log n}=n^2 < n^{\log n} < 2^n < n2^n < 2^{2n}.
\]

# Problem 3: Maximum Unhappiness for Gale-Shapley (20 points, 5 extra credit points available)
Let integer $n\geq 2$. Let's say that we run the Gale-Shapley algorithm on groups $A=\{a_1,\ldots,a_n\}$ and $B=\{b_1,\ldots,b_n\}$ with group $A$ making the offers.
- (a) 10 points: Is it possible that everyone in group $B$ is matched with their least preferred partner? Either give preference lists where this occurs (your construction should be in terms of $n$) or prove that this is impossible.

**Solution:** Yes. For each $i\in[n]$, let $a_i$ have $b_i$ as their first choice and let $b_i$ have $a_i$ as their last choice. Hence, each $a_i$ will make an offer to $b_i$, who will accept because they are available, and the algorithm will terminate with no rejections.

- (b) 10 points: Is it possible that everyone in group $A$ is matched with their least preferred partner? Either give preference lists where this occurs (your construction should be in terms of $n$) or prove that this is impossible.<br>
Hint is available.

**Solution:** This is impossible for $n\geq 2$. Consider the first time any member of group $A$, denoted $a_i$, makes an offer to their least preferred partner, denoted $b_j$. At this point, every other member of group $B$ must have been unavailable to $a_i$. As unavailable partners never become available again (Lemma 1.6), every other member of group $B$ is currently matched so there are at least $n-1$ matchings. As $a_i$ is unmatched, there are at most $n-1$ matchings. Hence, there are exactly $n-1$ matchings and every member of group $B$ except $b_j$ is matched, so $b_j$ is available and will accept $a_i$'s offer. The algorithm will then terminate. Therefore, at most one member in group $A$ can be matched with their least preferred partner.

- (c) 5 points extra credit: What is the maximum total number of offers that group $A$ has to make before a stable matching is reached (in terms of $n$)? For full extra credit, you should give preference lists where this maximum is obtained and explain why this maximum is obtained.

**Solution:** In part (b), we proved that at most 1 member of group $A$ can be matched with their least preferred partner. To maximize the number of offers, we ask if the next “worst-case” scenario is possible: one member of group $A$ being matched to their least preferred partner, and every other member being matched to their second-least preferred partner. This would result in $(n-1)(n-1)+n=n^2-n+1$ offers.

One set of preference lists for which this occurs is as follows:
$$
a_1 &: b_1,b_2,\ldots,b_{n-2},b_{n-1},b_n\\
a_2 &: b_2,b_3,\ldots,b_{n-1},b_1,b_n\\
&\vdots\\
a_{n-1} &: b_{n-1},b_1,\ldots,b_{n-3},b_{n-2},b_n\\
a_n &: b_1,b_2,\ldots,b_{n-2},b_{n-1},b_n\\[4pt]
b_1 &: a_2,a_3,\ldots,a_{n-1},a_n,a_1\\
b_2 &: a_3,a_4,\ldots,a_n,a_1,a_2\\
&\vdots\\
b_{n-1} &: a_n,a_1,\ldots,a_{n-3},a_{n-2},a_{n-1}\\
b_n &: a_1,a_2,\ldots,a_{n-2},a_{n-1},a_n
$$

(actually, any preference list for $b_n$ would work)

If we run G-S with group $A$ making the offers, we can have the people in group $A$ make offers in clockwise order $(a_1,\ldots,a_n)$. This goes through $n-1$ cycles. For all $i\in[n]$ and $j\in[n-1]$, $a_i$ makes its $j$th offer to $b_{(i+j-1)\bmod (n-1)}$ and this offer is accepted, displacing $a_{(i+1)\bmod n}$ if $j>1$ or $i=n$.

After everyone in group $A$ has made $n-1$ offers, $a_1$ is unmatched and makes an offer to $b_n$ which gives the final matching $M=\{(a_1,b_n),(a_2,b_1),\ldots,(a_n,b_{n-1})\}$.

# Problem 4: Lying Gale-Shapley? (20 points)
Give an example of the Stable Matching Problem for $n=3$, i.e., the groups are $A=\{a_1,a_2,a_3\}$ and $B=\{b_1,b_2,b_3\}$ with group $A$ making the offers, that satisfies the following property:
- One of the $B$'s can lie---during the execution of the Gale-Shapley algorithm she may decide to accept or reject an offer differently from what the algorithm tells her to do based on her true preferences. She can lie only once, but because of her lie, the solution will yield a stable matching, where at least one of the $B$'s gets a partner that she prefers to the one she gets in the honest execution, and none of the $B$'s gets a worse partner.

You should specify the preference lists, simulate the honest execution, point out where a lie should occur, and simulate the execution with the lie, verifying that the outcome is as claimed above.

**One possible solution:**
$$
a_1 &: b_1,b_2,b_3\\
a_2 &: b_1,b_3,b_2\\
a_3 &: b_2,b_1,b_3\\[4pt]
b_1 &: a_3,a_1,a_2\\
b_2 &: a_1,a_3,a_2\\
b_3 &: a_2,a_1,a_3
$$

**Honest execution:**
- $a_1$ makes offer to $b_1$: accepted as $b_1$ is unmatched

Current partial matching: $(a_1,b_1)$
- $a_2$ makes offer to $b_1$: rejected as $b_1$ prefers $a_1$ to $a_2$ $\leftarrow$ lie should occur here

Current partial matching: $(a_1,b_1)$
- $a_3$ makes offer to $b_2$: accepted as $b_2$ is unmatched

Current partial matching: $(a_1,b_1)$, $(a_3,b_2)$
- $a_2$ makes offer to $b_3$: accepted as $b_3$ is unmatched

Final matching: $(a_1,b_1)$, $(a_3,b_2)$, $(a_2,b_3)$

**Execution with lie:**
- $a_1$ makes offer to $b_1$: accepted as $b_1$ is unmatched

Current partial matching: $(a_1,b_1)$
- $a_2$ makes offer to $b_1$: (lie) accepted although $b_1$ prefers $a_1$ to $a_2$

Current partial matching: $(a_2,b_1)$
- $a_3$ makes offer to $b_2$: accepted as $b_2$ is unmatched

Current partial matching: $(a_2,b_1)$, $(a_3,b_2)$
- $a_1$ makes offer to $b_2$: accepted as $b_2$ prefers $a_1$ to $a_3$

Current partial matching: $(a_2,b_1)$, $(a_1,b_2)$
- $a_3$ makes offer to $b_1$: accepted as $b_1$ prefers $a_3$ to $a_2$

Current partial matching: $(a_1,b_2)$, $(a_3,b_1)$
- $a_2$ makes offer to $b_3$: accepted as $b_3$ is unmatched

Final matching: $(a_1,b_2)$, $(a_3,b_1)$, $(a_2,b_3)$

$b_1$ and $b_2$ get partners they prefer and $b_3$ gets the same partner.

# Hints
1c. Use parts a and b and the properties of the Gale-Shapley algorithm to determine the set of possible partners for each person in a stable matching and then work from there.<br>
<br>
2b. Taking the logarithm of these functions may be helpful for comparing them.<br>
<br>
3b. Can you make the upper bound on the total number of offers be less than $n^2$?

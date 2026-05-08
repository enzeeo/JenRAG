# CMSC 27100—Problem Set 1 Solutions

*University of Chicago, Autumn 2025*

## Solutions

### 1. Prove that for all natural numbers $m,n,p$, we have

$$
m \times (n+p) = m \times n + m \times p.
$$

**Solution.** First, we define $m \times n$ for natural numbers $m$ and $n$ by
- if $m=z$, then $m \times n = z \times n = z$, and
- if $m=\operatorname{succ}(k)$ for some natural number $k$, then
  $m \times n = \operatorname{succ}(k) \times n = n + k \times n$.

We will prove that $m \times (n+p)=m\times n+m\times p$ by induction on $m$.

**Base case.** If $m=z$, then

$$
\begin{aligned}
m \times (n+p) &= z \times (n+p) && \text{Premise} \\
  &= z && \text{Multiplication} \\
  &= z+z && \text{Addition} \\
  &= z\times n + z && \text{Multiplication} \\
  &= z\times n + z\times p && \text{Multiplication} \\
  &= m\times n + m\times p && \text{Premise.}
\end{aligned}
$$

**Inductive case.** Let $m=\operatorname{succ}(k)$ where $k$ is an arbitrary natural number.
Assume that

$$
k \times (n+p) = k \times n + k \times p.
$$

Then we have

$$
\begin{aligned}
m \times (n+p)
  &= \operatorname{succ}(k) \times (n+p) && \text{Premise} \\
  &= (n+p) + k \times (n+p) && \text{Multiplication} \\
  &= (n+p) + (k\times n + k\times p) && \text{Inductive hypothesis} \\
  &= n + (p + (k\times n + k\times p)) && \text{Associativity of addition} \\
  &= n + ((p+k\times n)+k\times p) && \text{Associativity of addition} \\
  &= n + ((k\times n+p)+k\times p) && \text{Commutativity of addition} \\
  &= n + (k\times n + (p+k\times p)) && \text{Associativity of addition} \\
  &= n + (k\times n + \operatorname{succ}(k)\times p) && \text{Multiplication} \\
  &= (n+k\times n) + \operatorname{succ}(k)\times p && \text{Associativity of addition} \\
  &= \operatorname{succ}(k)\times n + \operatorname{succ}(k)\times p && \text{Multiplication} \\
  &= m\times n + m\times p && \text{Premise.}
\end{aligned}
$$

**Notes.**
- The property that is being proved in this problem is distributivity of multiplication over addition.
- Note that a slightly different definition of multiplication can be used, for instance, expanding on $n$ instead of $m$. The proof will change depending on your definition.
- Notice that the use of associativity and commutativity of addition are noted explicitly. It is important in proofs of fundamental facts like this to be extra careful in applying definitions and known results to ensure that we do not take any shortcuts we are not allowed to.

### 2. Prove that for every propositional sentence $p$ over the propositional variables
$x_1,x_2,\ldots$, there is a logically equivalent propositional sentence that uses only the Sheffer stroke.

**Solution.** We will prove this by induction on the propositional sentence $p$.

**Base case.** In this case, $p=x$, where $x$ is a propositional variable from $x_1,x_2,\ldots$.
Since the sentence is just a propositional variable on its own, it vacuously uses only the Sheffer stroke.
Alternatively, it does not use any connective that is not the Sheffer stroke.

**Inductive case.** Let $q$ and $r$ be arbitrary propositional sentences and assume that $q$ and $r$ are written using only the Sheffer stroke connective. We have four cases.
- If $p=\neg q$, then $p\equiv q\uparrow q$ by the truth table
  
$$
\begin{array}{c|c|c}
  q & \neg q & q\uparrow q \\
  \hline
  T & F & F \\
  F & T & T
  \end{array}
$$
- If $p=q\land r$, then $p\equiv (q\uparrow r)\uparrow(q\uparrow r)$ by the truth table
  
$$
\begin{array}{c|c|c|c|c}
  q & r & q\land r & q\uparrow r & (q\uparrow r)\uparrow(q\uparrow r) \\
  \hline
  T & T & T & F & T \\
  T & F & F & T & F \\
  F & T & F & T & F \\
  F & F & F & T & F
  \end{array}
$$

  One way to think about this is that $\neg(q\land r)\equiv q\uparrow r$. So really, we are looking for a way to negate $q\uparrow r$, which we did in the previous case.
- If $p=q\lor r$, then $p\equiv (q\uparrow q)\uparrow(r\uparrow r)$ by the truth table
  
$$
\begin{array}{c|c|c|c|c|c}
  q & r & q\lor r & q\uparrow q & r\uparrow r & (q\uparrow q)\uparrow(r\uparrow r) \\
  \hline
  T & T & T & F & F & T \\
  T & F & T & F & T & T \\
  F & T & T & T & F & T \\
  F & F & F & T & T & F
  \end{array}
$$

  To see this, we observe that by De Morgan's laws, $p\lor q\equiv \neg(\neg p\land\neg q)$.
  We also see that $\neg(\neg p\land\neg q)\equiv \neg p\uparrow\neg q$ and $\neg p\equiv p\uparrow p$ from above.
- If $p=q\to r$, then $p\equiv q\uparrow(r\uparrow r)$ by the truth table
  
$$
\begin{array}{c|c|c|c|c}
  q & r & q\to r & r\uparrow r & q\uparrow(r\uparrow r) \\
  \hline
  T & T & T & F & T \\
  T & F & F & T & F \\
  F & T & T & F & T \\
  F & F & T & T & T
  \end{array}
$$

  This one takes a bit more work, since one needs to arrive at the fact that $p\to q\equiv \neg p\lor q$.
  This can be seen easily via truth table, but takes a bit of reasoning to get to via proof. However, once you view this as a conjunction, it is straightforward to use De Morgan's laws and the previous cases to get to the result.

**Notes.** Observe that this proof really gives a recursive algorithm for rewriting an arbitrary propositional sentence using only $\uparrow$. This is a consequence of the formal inductive argument.

### 3. Prove that for all integers $x$ and sorted lists of integers $L$, the list $x\rightsquigarrow L$ is a non-empty sorted list of integers.

**Solution.** We will prove this by induction on $L$. Let $x$ be an arbitrary integer.

**Base case.** If $L=\langle\rangle$ is empty, then by definition of $\rightsquigarrow$,
$x\rightsquigarrow L=\langle x,\langle\rangle\rangle$. This is a non-empty sorted list of integers, by Definition 3.

**Inductive case.** Let $L=\langle y,L'\rangle$, where $y$ is an integer and $L'$ is a sorted list of integers.
Assume that $x\rightsquigarrow L'$ is a sorted list of integers. There are two cases.
- If $x<y$, then $x\rightsquigarrow L=\langle x,\langle y,L'\rangle\rangle$.
  Since $\langle y,L'\rangle$ is a nonempty sorted list of integers and $x<y$, $x\rightsquigarrow L$ is a non-empty sorted list of integers by Definition 3.
- Otherwise, if $x\ge y$, then $x\rightsquigarrow L=\langle y,x\rightsquigarrow L'\rangle$.
  By our inductive hypothesis, $x\rightsquigarrow L'$ is a sorted list of integers. Since $\langle y,L'\rangle$ is a sorted list of integers, we have that $z\ge y$ for all $z$ in $L'$.
  And since $x\ge y$, we have that $z\ge y$ for all $z$ in $x\rightsquigarrow L'$.
  So $x\rightsquigarrow L$ is a non-empty sorted list of integers.

**Notes.** The function $x\rightsquigarrow L$ is the insertion function used in insertion sort. We can translate this to Python:

```python
def insert(x: int, lst: list[int]) -> list[int]:
    match lst:
        case []:
            return [x]
        case y, *rest:
            if x < y:
                return [x] + lst
            else:
                return [y] + insert(x, rest)
```

Then we can also write insertion sort recursively and use `insert` from above:

```python
def insertion_sort(lst: list[int]) -> list[int]:
    match lst:
        case []:
            return []
        case first, *rest:
            return insert(first, insertion_sort(rest))
```

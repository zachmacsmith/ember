# A066 diagnostic: exact two-owner contact domains

2026-09-10. Exploration only; no new constructor and no global optimization.

**Hypothesis.** The final A065 states contain two-site chains that cannot become
singletons with all neighbors fixed, but can do so after a neighboring singleton
moves at equal Q. Such a witness separates a strict-Q acceptance limitation from
absence of a feasible neutral relocation. A joint-release witness that lacks a
valid intermediate supports a different, coordinated move neighborhood.

Use exactly the saved A065 seed-0 final maps on g0001, g0006, g0013, g0017, g0201,
and g0202. Bind their original source/target records and audited candidate result
bytes; do not read MM result maps or private synthetic witnesses. Source IDs
select diagnostic inputs only and never influence the domain operator.

```text
validate the complete entry with the unchanged independent oracle
for each source edge (u,v) with |C(u)|=2 and |C(v)|=1:
    compute exact singleton domain of u with all other owners fixed
    release u and v; intersect free sites with each outside contact boundary
    enumerate actual hardware edges p--q between the two resulting domains
    classify q as a valid neutral relocation iff it is disjoint from old C(u)
        and adjacent to old C(u), preserving every outside contact
    retain canonical witnesses for available direct, neutral-first, and
        joint-release-only assignment categories
    independently validate each retained complete map and neutral intermediate
    use unchanged A063 preparation to report donor savings for u
```

The domain is finite and exact for this **two-singleton** primitive. “Joint-only”
means no neutral-first witness exists among these assignments; a pair may also
have both kinds, which must remain distinguishable. Direct shortening availability
is reported separately; only its absence supports the necessity of changing v.
When direct shortening is absent and the unchanged A063 preparation releases
zero donor sites, the current strict-Q query for u cannot improve: a two-site
focus must become a singleton and every other chain remains fixed. This is a
query/acceptance observation, not a restriction of arbitrary connected-chain
representation. Do not extrapolate it to larger chains or other owners.

**Allocation and falsifier.** Six fresh isolated local processes, 30 seconds of
wall time per input from worker entry through setup, preparation, enumeration,
validation and result production. A kernel timer bounds interruption; an outer
45-second process timeout records any missing worker result. No work counter,
root limit or pair cap terminates search. Complete the input if its finite domain
ends sooner. Preserve phase time, CPU/process time, all processed/remaining
pairs, errors, interrupted witness validations and binding failures. A timed-out
pair is unknown; never count it as a negative. Local timings describe this
instrument, not a comparison with MM or a complete constructor.

No neutral bridge on any fully exhausted input rejects this primitive as the
immediate acceptance-rule integration target. Only simultaneous-release witnesses
support redesign toward joint replacement. Independently valid neutral-first
witnesses on at least two distinct structures warrant a promptly specified small
complete-constructor screen; they do not themselves promote an algorithm.

**Self-critique.** Restricting u/v to lengths two/one can miss larger or uphill
rearrangements. Easy local savings may disappear once composed with construction;
prior direct-singleton and vacancy approaches did not establish all-class wins.
The canonical witness order is arbitrary and has no demonstrated quality value.
Validation overhead can censor a domain that the production operator could scan
cheaply; report it separately while charging it. Reusing A063 preparation adds
only attribution, never candidate embedding initialization. A positive map is
one private modification of an existing candidate state, not a portfolio.

Before execution, freeze all code, this contract and candidate-only input hashes.
Focused checks cover direct-versus-neutral-versus-joint classification against a
brute-force oracle on tiny graphs, occupied-site/contact exclusions, exact donor
attribution through the unchanged preparation, and interruption accounting.

# Design proposal: restrict reductions to degree at most two

Unimplemented alternative within track A, 2026-09-08. Finish the already fixed A053 transfer experiment before selecting this next test. This proposal does not alter A053 or choose between completed outputs.

**Hypothesis.** Keeping degree-three junctions in the constructed core may avoid part of the artificial contact burden observed in the reduced-core line. Suppressing a degree-two source vertex is a graph-minor operation; replacing a degree-three star by a triangle generally is not. Restrict the existing elimination rule to degree at most two, while retaining the same anchors, fixed native core constructor, reverse expansion and any independently retained transfer mechanism. The comparison would use one fixed ancestor and one fixed reduction change.

The distinction has a direct proof. If v has two distinct remaining neighbors a and b, contracting edge a–v produces exactly the graph obtained by deleting v and adding a–b, with duplicate edges ignored. Degree-zero/one removal is vertex deletion. Repeating these operations leaves a core that is a minor of the original source. Given any original embedding, unite the connected chains of contracted source vertices to obtain a core embedding using at most the same total physical sites. Thus the *optimal* core qubit count cannot exceed the original optimum. This does not make the heuristic's particular core output optimal or guarantee a cheap reverse lift.

By contrast, a degree-three star can be replaced by a triangle by clique fill, although no triangle is a minor of that star. This is an operator-level counterexample, not a claim that the present protected-anchor/minimum-degree ordering actually eliminates the center of that isolated star. The current degree-three algorithm remains a valid heuristic when its final original minor passes validation; its stronger intermediate requirements can simply be expensive.

```text
retain the existing protected anchors and deterministic tie ranks
while an unprotected vertex has current filled degree at most two:
    record its remaining neighbors and only its newly created fill edge
    remove the vertex, joining its two neighbors when necessary
construct the remaining filled core once with the fixed native configuration
reverse the journal using the unchanged selected expansion policy
validate the final original minor and returned time
```

**Cheap falsifier before a corpus screen.** If chosen next, first specify the exact ancestor and unchanged limits. Verify the series-contraction identity on a few fixed small original graphs, preserving original-edge versus created-fill provenance. Run the same fixed reach inputs already used in this line and report every failure, Q and total time. A read-only reduction comparison on the existing development inputs can identify which cores/orders would change, but it cannot establish an embedding improvement. The mechanism is uninteresting if it changes no relevant reductions, loses basic reach, or fails to improve final quality despite the stronger minor relationship. No input-specific threshold or alternate completed output is allowed.

**Self-critique.** Degree-three elimination provides most of the reduction on cubic or other low-degree graphs. Keeping those vertices can remove useful simplification and make this policy behave like the unchanged native constructor on many inputs. Even a minor core can be placed poorly for its eventual lift; the original-only experiment already showed that cheaper cores need not yield cheaper full embeddings. Series suppression can still crowd pending contacts, and a one-site transfer may be unavailable. A theoretical relation between optimum costs is not evidence that this particular search achieves them. This is a conventional reduction property, with no novelty, runtime advantage or all-class superiority claim.

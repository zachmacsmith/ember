# B020/C007 constructor registration

The shared pilot now routes `movable-contact-trees` and `movable-contact-single` to their respective factored `contact_embed` entrypoints, and `variable-regions`/`atomic-regions` to `variable_embed`/`atomic_embed`. All four configurations are exactly `{}`; their existing common deadline, source copies, isolated import and original-graph validation paths are reused.

One passive worker field copies `response.get('diagnostic_embedding')` beside `partial_embedding`. It never enters primary embedding validation, status selection or quality computation. Missing diagnostic output remains null. Both FAILED and timely TIMEOUT stub responses with an otherwise valid map only in this field remain uncredited, while their full diagnostic map survives JSON publication.

Six focused tests passed on the first execution: the four existing dispatch cases plus the two diagnostic-only outcomes (1.08 s). Each worker ran in the isolated native environment and checked that no prohibited imports occurred. No constructor implementation, corpus, comparator or remote call was executed. The remaining pilot AST is byte-independent identical after removing exactly the four registry entries and passive assignment; existing configurations and control flow are untouched. The only warning was the existing test setup's dwave-networkx deprecation.

Evidence: `results/codex/b020-c007-registration/` preserves prior pilot/test bytes, exact diff, pre-execution command/hash record, raw output and final status. Pilot SHA256: `2033f14cc3198a89a00fabe792e7b6d3fae8fa392f495f24eb81112aa0f762fc`; test SHA256: `e49ab029af65708caec7f928378cdaca0278131dad723aaece1ec9a35c16b127`. Frozen 055/056 snapshots are unchanged.

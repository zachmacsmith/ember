"""A067: choose one shared-tree attachment by actual contact coverage per site.

The A066 search, donor preparation, roots, admission and pair operator are reused.
Only ordinary reconstruction's attachment selection changes. No intermediate-Q
cap: final trimming can remove the initial root and obsolete branches.
"""
import math
import time

from ember_qc.algorithms.factored.compiled_boundary_reconstruction import _Context as _OldContext
from ember_qc.algorithms.factored.paired_boundary_reconstruction import _Search
from ember_qc.algorithms.factored.mobile_boundary_reconstruction import _Meter, _Stop


# The package supports Python 3.9; int.bit_count starts in Python 3.10.
# The frozen native environment uses the fast descriptor. Both count arbitrary
# nonnegative integer masks exactly; neither imposes a width limit.
def _portable_bit_count(mask):
    return bin(mask).count('1')


_bit_count = getattr(int, 'bit_count', _portable_bit_count)


class _Context(_OldContext):
    def coverage_path(self, tree, missing, free, boundary, group_bits, site_masks):
        """Return one reverse path and its junction in tree; never change tree.

        Each site has the first predecessor found by the existing seeded BFS
        traversal. Its mask describes that one actual shortest path, not all
        equal-length alternatives. Integer masks have no fixed group-count cap.
        """
        self.m.tick('coverage_searches')
        missing_mask = 0
        for v in missing:
            self.m.tick('coverage_missing_group')
            missing_mask |= group_bits[v]
        remaining = len(missing)
        words = max(1, (len(group_bits)+63)//64)

        def contact_mask(q):
            if q not in site_masks:
                mask = 0
                for v in boundary.get(q, ()):
                    self.m.tick('coverage_site_contact')
                    mask |= group_bits[v]
                site_masks[q] = mask
            self.m.tick('coverage_mask_intersection', words)
            return site_masks[q] & missing_mask

        level = self.m.ordered(tree, key=self.qtie.__getitem__)
        pred = {q: None for q in level}
        masks = dict.fromkeys(level, 0)
        self.m.tick('tree_bfs_sources', len(level))
        distance, chosen, best_length, best_gain = 0, None, None, None
        while level:
            self.m.tick('coverage_bound_check')
            if chosen is not None and distance*best_gain > best_length*remaining:
                # At most `remaining` groups can be contacted by any path.
                # Strict > preserves the entire tied layer. This proves only
                # that deeper canonical paths cannot improve this local score.
                self.m.tick('coverage_bound_closed')
                break
            following = []
            for q in level:
                self.m.check(); self.m.tick('tree_bfs_pop')
                self.m.tick('coverage_mask_popcount', words)
                gain = _bit_count(masks[q])
                if gain:
                    self.m.tick('coverage_candidate')
                    better = (chosen is None or distance*best_gain < best_length*gain)
                    if not better and distance*best_gain == best_length*gain:
                        better = (distance, self.qtie[q]) < (best_length, self.qtie[chosen])
                    if better:
                        chosen, best_length, best_gain = q, distance, gain
                for p in self.target[q]:
                    self.m.tick('tree_bfs_edge')
                    if p in free and p not in pred:
                        pred[p] = q
                        self.m.tick('coverage_mask_union', words)
                        masks[p] = masks[q] | contact_mask(p)
                        following.append(p)
            level = following
            distance += 1
        else:
            self.m.tick('coverage_search_exhausted')
        if chosen is None:
            raise RuntimeError('ranked root lost shared-path reach')
        path, q = [], chosen
        while q not in tree:
            self.m.tick('extension_site'); path.append(q); q = pred[q]
        if len(path) != best_length or not path:
            raise RuntimeError('contact-coverage path length mismatch')
        self.m.tick('coverage_extensions')
        self.m.tick('coverage_sites_added', len(path))
        self.m.tick('coverage_groups_gained', best_gain)
        return path, q

    def reconstruct(self, root, reduced, free, boundary, u):
        self.m.phase_to('reconstruction')
        tree = {root: set()}
        missing = set(reduced)
        self.m.tick('unmet_neighbors', len(missing))
        group_bits = {}
        for index, v in enumerate(reduced):
            self.m.tick('coverage_group_bit')
            group_bits[v] = 1 << index
        site_masks = {}
        while True:
            for q in tree:
                self.m.tick('tree_contact_site')
                for v in boundary.get(q, ()):
                    self.m.tick('tree_contact'); missing.discard(v)
            if not missing:
                break
            path, q = self.coverage_path(tree, missing, free, boundary, group_bits, site_masks)
            self.m.tick('shared_tree_junction')
            for p in reversed(path):
                self.m.tick('extension_publish')
                tree[p] = {q}; tree[q].add(p); q = p
        # Original A063 witness selection and trimming, unchanged.
        witnesses, retained_owner = {}, {}
        for v, sites in reduced.items():
            for q in sites:
                self.m.tick('retained_witness_site'); retained_owner[q] = v
        for q in tree:
            self.m.tick('new_contact_site')
            for p in self.target[q]:
                self.m.tick('new_contact_edge')
                if p in retained_owner:
                    v = retained_owner[p]
                    pair = (q, p) if u < v else (p, q)
                    if v not in witnesses or pair < witnesses[v]:
                        witnesses[v] = pair
        terminals = {pair[0 if u < v else 1] for v, pair in witnesses.items()} if reduced else {min(tree)}
        if len(witnesses) != len(reduced):
            raise RuntimeError('constructed tree lacks required terminal')
        return self.trim(tree, terminals)


def contact_coverage_reconstruction(embedding, source_adj, target_adj, *, seed=0,
                                    deadline, validator, enable_pairs=True):
    """A066's operator lifecycle with the new reconstruction context only."""
    if type(seed) is not int or not isinstance(deadline, (int, float)) or not math.isfinite(deadline):
        raise ValueError('integer seed and finite absolute deadline required')
    m = _Meter(deadline)
    info = dict(algorithm='contact_coverage_reconstruction', version='A067',
                status='started', error=None, input_copy_complete=False, input_validated=False,
                rounds_started=0, rounds_completed=0, rounds=[], queries=[], commits=[], epochs=[],
                epoch=0, accepted=0, before_qubits=None, after_qubits=None,
                stopped_phase=None, diagnostic_embedding=None)
    current, search, result = None, None, embedding
    try:
        m.check()
        ctx = _Context(source_adj, target_adj, seed, validator, m)
        chains = ctx.read_entry(embedding)
        result = ctx.externalize(chains)
        info['input_copy_complete'] = True
        ctx.certify(chains)
        current = ctx.bundle(chains)
        result = current.external
        info.update(input_validated=True, before_qubits=current.qubits)
        search = _Search(ctx, current, info, enable_pairs=enable_pairs)
        search.run()
    except _Stop:
        info.update(status='deadline', stopped_phase=m.phase)
    except Exception as exc:
        info.update(status='error', error=type(exc).__name__+': '+str(exc), stopped_phase=m.phase)
    finally:
        if search is not None:
            current = search.current
            result = current.external
            try:
                search.cleanup()
            except _Stop:
                info['cleanup_deadline'] = True
                if info['status'] not in ('error', 'deadline'):
                    info.update(status='deadline', stopped_phase=m.phase)
            except Exception as exc:
                info.update(status='error', error=type(exc).__name__+': '+str(exc), stopped_phase=m.phase)
    if info['error'] is not None:
        info['diagnostic_embedding'] = current.external if current is not None else embedding
        result = {}
    info['after_qubits'] = current.qubits if current is not None else None
    info.update(m.finish())
    if info['ended'] >= deadline and info['status'] not in ('error', 'deadline'):
        info.update(status='deadline', stopped_phase=m.phase)
    return result, info

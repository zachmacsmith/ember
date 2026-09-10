"""Convert active supports with the unchanged physical lane converter."""
from ember_qc.algorithms.factored.field import _convert_line

def arm_targets(pos, bk, orientation):
    axis = 0 if orientation == 1 else 1
    targets = {}
    for _, _, _, v in bk.tuples[orientation]:
        required = bk.supports[v][axis]
        if not required or bk.bars[v][axis] is None:
            raise RuntimeError('physical arm lacks active support')
        lines = sorted({int(round(float(pos[u][axis]))) for u in required})
        a, b = bk.bars[v][axis]
        targets[v] = (a, b, lines)
    return targets

def wire_seeds(grid, pos, bk):
    # Inactive virtual claims never enter this function's physical consumers.
    claimed, chains = set(), {v: [] for v in pos}
    info = dict(convert_miss=0, convert_flips=0,
                physical_arms=sum(map(len,bk.tuples.values())),
                virtual_arms=sum(map(len,bk.capacity.values()))-sum(map(len,bk.tuples.values())),
                inactive_booking=bk.inactive_booking)
    for orientation in (1, 0):
        targets = arm_targets(pos, bk, orientation)
        by_line = {}
        for line, a, b, v in bk.tuples[orientation]:
            by_line.setdefault(line, []).append((a,b,v))
        for line, items in sorted(by_line.items()):
            missed, flips = _convert_line(grid, claimed, chains, orientation,
                                          line, items, targets)
            info['convert_miss'] += missed
            info['convert_flips'] += flips
    # Do not manufacture a corner for missing arms or isolates. The native
    # wrapper retains its ordinary free-site isolate allocation and unchanged
    # completion/validation; a missing non-isolate remains visible as failure.
    return {v: chain for v,chain in chains.items() if chain}, info

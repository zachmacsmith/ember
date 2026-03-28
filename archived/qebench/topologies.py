"""
Topology registry for QEBench.

Built-in D-Wave topologies (chimera, pegasus, zephyr) at multiple sizes,
plus support for registering custom/hypothetical hardware graphs.

Usage:
    from qebench.topologies import get_topology, list_topologies

    chimera = get_topology("chimera_4x4x4")
    print(list_topologies())

    # Register a custom topology
    from qebench.topologies import register_topology
    register_topology(
        "hex_lattice",
        family="custom",
        generator=lambda: nx.hexagonal_lattice_graph(10, 10),
        params={"rows": 10, "cols": 10},
        description="Hypothetical hexagonal lattice"
    )
"""

import networkx as nx
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class TopologyConfig:
    """Configuration for a hardware topology."""
    name: str                   # e.g., "chimera_4x4x4"
    family: str                 # e.g., "chimera", "pegasus", "custom"
    generator: Callable         # function() -> nx.Graph
    params: Dict                # e.g., {"m": 4, "n": 4, "t": 4}
    description: str = ""       # e.g., "Chimera 4×4×4 (128 qubits)"
    _cached_graph: Optional[nx.Graph] = field(default=None, repr=False)


# Global registry
TOPOLOGY_REGISTRY: Dict[str, TopologyConfig] = {}


def register_topology(name: str, family: str, generator: Callable,
                       params: dict, description: str = ""):
    """Register a topology in the global registry.
    
    Args:
        name: Unique identifier (e.g., "chimera_4x4x4").
        family: Topology family (e.g., "chimera", "pegasus", "custom").
        generator: Callable that returns a NetworkX graph.
        params: Dict of parameters used by the generator.
        description: Human-readable description.
    """
    TOPOLOGY_REGISTRY[name] = TopologyConfig(
        name=name, family=family, generator=generator,
        params=params, description=description
    )


def get_topology(name: str) -> nx.Graph:
    """Get a topology graph by name. Generated on first call, cached after.
    
    Args:
        name: Registered topology name (e.g., "chimera_4x4x4").
        
    Returns:
        NetworkX graph for the topology.
        
    Raises:
        ValueError: If the topology name is not registered.
    """
    if name not in TOPOLOGY_REGISTRY:
        raise ValueError(
            f"Unknown topology '{name}'. "
            f"Available: {list(TOPOLOGY_REGISTRY.keys())}"
        )
    config = TOPOLOGY_REGISTRY[name]
    if config._cached_graph is None:
        config._cached_graph = config.generator()
    return config._cached_graph


def get_topology_config(name: str) -> TopologyConfig:
    """Get the full config for a topology."""
    if name not in TOPOLOGY_REGISTRY:
        raise ValueError(f"Unknown topology '{name}'.")
    return TOPOLOGY_REGISTRY[name]


def list_topologies(family: str = None) -> List[str]:
    """List all registered topology names, optionally filtered by family.
    
    Args:
        family: If provided, only return topologies of this family.
        
    Returns:
        Sorted list of topology names.
    """
    if family:
        return sorted(n for n, c in TOPOLOGY_REGISTRY.items() if c.family == family)
    return sorted(TOPOLOGY_REGISTRY.keys())


def list_topology_families() -> List[str]:
    """List all unique topology families."""
    return sorted(set(c.family for c in TOPOLOGY_REGISTRY.values()))


def topology_info() -> str:
    """Return a formatted string with all registered topologies."""
    lines = ["Registered topologies:", ""]
    lines.append(f"{'Name':<25} {'Family':<12} {'Qubits':>8}  {'Edges':>8}  Description")
    lines.append("-" * 85)
    for name in sorted(TOPOLOGY_REGISTRY.keys()):
        config = TOPOLOGY_REGISTRY[name]
        g = get_topology(name)
        lines.append(
            f"{name:<25} {config.family:<12} {g.number_of_nodes():>8}  "
            f"{g.number_of_edges():>8}  {config.description}"
        )
    return "\n".join(lines)


# =============================================================================
# Built-in D-Wave topologies
# =============================================================================

def _register_builtins():
    """Register all built-in D-Wave topologies."""
    import dwave_networkx as dnx
    
    # --- Chimera ---
    chimera_sizes = [
        (4, 4, 4, "Small test size"),
        (8, 8, 4, "Medium"),
        (12, 12, 4, "Large"),
        (16, 16, 4, "D-Wave 2000Q"),
    ]
    for m, n, t, desc in chimera_sizes:
        name = f"chimera_{m}x{n}x{t}"
        register_topology(
            name, family="chimera",
            generator=lambda m=m, n=n, t=t: dnx.chimera_graph(m, n, t),
            params={"m": m, "n": n, "t": t},
            description=f"Chimera {m}×{n}×{t} ({desc})"
        )
    
    # --- Pegasus ---
    pegasus_sizes = [
        (4, "Small test size"),
        (6, "Medium"),
        (8, "Large"),
        (16, "D-Wave Advantage"),
    ]
    for m, desc in pegasus_sizes:
        name = f"pegasus_{m}"
        register_topology(
            name, family="pegasus",
            generator=lambda m=m: dnx.pegasus_graph(m),
            params={"m": m},
            description=f"Pegasus P{m} ({desc})"
        )
    
    # --- Zephyr ---
    zephyr_sizes = [
        (2, "Small test size"),
        (4, "Medium"),
        (6, "Large"),
        (12, "Advantage2 prototype"),
    ]
    for m, desc in zephyr_sizes:
        name = f"zephyr_{m}"
        register_topology(
            name, family="zephyr",
            generator=lambda m=m: dnx.zephyr_graph(m),
            params={"m": m},
            description=f"Zephyr Z{m} ({desc})"
        )


# Auto-register builtins on import
_register_builtins()

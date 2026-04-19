"""
ember_qc/algorithms/minorminer.py
===================================
D-Wave minorminer variants and clique embedding.
"""

import logging
import time

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

logger = logging.getLogger(__name__)


@register_algorithm("minorminer")
class MinorMinerAlgorithm(EmbeddingAlgorithm):
    """D-Wave minorminer — industry-standard heuristic embedding."""

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        start_time = time.time()
        try:
            import minorminer
            seed = kwargs.get('seed', 42)
            # Pass the source as a graph object (not an edge list) so that
            # isolated source vertices are preserved and assigned singleton
            # chains. The edge-list form silently drops vertices with no
            # incident edges, producing INVALID_OUTPUT on near-edgeless graphs.
            embedding = minorminer.find_embedding(
                source_graph,
                list(target_graph.edges()),
                timeout=timeout,
                verbose=0,
                random_seed=seed,
            )
            elapsed = time.time() - start_time
            if not embedding:
                return {'embedding': {}, 'time': elapsed, 'success': False, 'status': 'FAILURE'}
            return {'embedding': embedding, 'time': elapsed}
        except Exception as e:
            logger.error("minorminer error: %s", e)
            return {'embedding': {}, 'time': time.time() - start_time, 'success': False, 'status': 'FAILURE'}


@register_algorithm("minorminer-aggressive")
class MinorMinerAggressive(EmbeddingAlgorithm):
    """CMR with more restarts — better quality, slower. (tries=50, max_no_improve=20)"""

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        start_time = time.time()
        try:
            import minorminer
            seed = kwargs.get('seed', 42)
            embedding = minorminer.find_embedding(
                source_graph,
                list(target_graph.edges()),
                timeout=timeout,
                verbose=0,
                tries=50,
                max_no_improvement=20,
                random_seed=seed,
            )
            elapsed = time.time() - start_time
            if not embedding:
                return {'embedding': {}, 'time': elapsed, 'success': False, 'status': 'FAILURE'}
            return {'embedding': embedding, 'time': elapsed}
        except Exception as e:
            logger.error("minorminer-aggressive error: %s", e)
            return {'embedding': {}, 'time': time.time() - start_time, 'success': False, 'status': 'FAILURE'}


@register_algorithm("minorminer-fast")
class MinorMinerFast(EmbeddingAlgorithm):
    """CMR with fewer restarts — fast but lower quality. (tries=3, max_no_improve=3)"""

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        start_time = time.time()
        try:
            import minorminer
            seed = kwargs.get('seed', 42)
            embedding = minorminer.find_embedding(
                source_graph,
                list(target_graph.edges()),
                timeout=timeout,
                verbose=0,
                tries=3,
                max_no_improvement=3,
                random_seed=seed,
            )
            elapsed = time.time() - start_time
            if not embedding:
                return {'embedding': {}, 'time': elapsed, 'success': False, 'status': 'FAILURE'}
            return {'embedding': embedding, 'time': elapsed}
        except Exception as e:
            logger.error("minorminer-fast error: %s", e)
            return {'embedding': {}, 'time': time.time() - start_time, 'success': False, 'status': 'FAILURE'}


@register_algorithm("minorminer-chainlength")
class MinorMinerChainLength(EmbeddingAlgorithm):
    """CMR optimised for short chains — slower but cleaner. (tries=20, chainlength_patience=20)"""

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        start_time = time.time()
        try:
            import minorminer
            seed = kwargs.get('seed', 42)
            embedding = minorminer.find_embedding(
                source_graph,
                list(target_graph.edges()),
                timeout=timeout,
                verbose=0,
                tries=20,
                chainlength_patience=20,
                random_seed=seed,
            )
            elapsed = time.time() - start_time
            if not embedding:
                return {'embedding': {}, 'time': elapsed, 'success': False, 'status': 'FAILURE'}
            return {'embedding': embedding, 'time': elapsed}
        except Exception as e:
            logger.error("minorminer-chainlength error: %s", e)
            return {'embedding': {}, 'time': time.time() - start_time, 'success': False, 'status': 'FAILURE'}


@register_algorithm("clique")
class CliqueEmbeddingAlgorithm(EmbeddingAlgorithm):
    """D-Wave clique embedding — topology-aware deterministic baseline."""

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        start_time = time.time()
        try:
            from minorminer.busclique import find_clique_embedding
            raw = find_clique_embedding(source_graph, target_graph)
            elapsed = time.time() - start_time
            if not raw:
                return {'embedding': {}, 'time': elapsed, 'success': False, 'status': 'FAILURE'}
            embedding = {k: list(v) for k, v in raw.items()}
            return {'embedding': embedding, 'time': elapsed}
        except Exception as e:
            logger.error("clique embedding error: %s", e)
            return {'embedding': {}, 'time': time.time() - start_time, 'success': False, 'status': 'FAILURE'}

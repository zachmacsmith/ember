"""
tests/conftest.py
=================
Shared pytest fixtures available to all test modules.
"""
import networkx as nx
import dwave_networkx as dnx
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_binary: mark test as requiring an installed C++ binary",
    )
    config.addinivalue_line(
        "markers",
        "requires_weights: mark test as requiring the CHARME weights file",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (can be excluded with -m 'not slow')",
    )


@pytest.fixture(scope="session")
def chimera_session():
    """Chimera(4,4,4) — 128 qubits. Session-scoped to avoid rebuilding."""
    return dnx.chimera_graph(4, 4, 4)


@pytest.fixture
def chimera():
    return dnx.chimera_graph(4, 4, 4)


@pytest.fixture
def K4():
    return nx.complete_graph(4)


@pytest.fixture
def K8():
    return nx.complete_graph(8)


@pytest.fixture
def cycle10():
    return nx.cycle_graph(10)


@pytest.fixture
def petersen():
    return nx.petersen_graph()

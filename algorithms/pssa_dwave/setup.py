from setuptools import setup, find_packages

setup(
    name="pssa_dwave",
    version="0.1.0",
    description="PSSA minor embedding algorithm for D-Wave hardware (Chimera, Pegasus, Zephyr)",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "networkx>=2.6",
        "numpy>=1.20",
        "dwave-networkx>=0.8",
        "minorminer>=0.2",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-cov"],
    },
)

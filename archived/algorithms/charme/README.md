# CHARME: Learning-Based Minor Embedding for Quantum Annealers

This repository contains the implementation of **CHARME**, a learning-based framework for solving the **Minor Embedding (ME)** problem on quantum annealing hardware. CHARME formulates minor embedding as a **sequential decision-making problem** and applies **reinforcement learning (PPO)** with **graph neural networks (GNNs)** to generate high-quality, hardware-aware embeddings.

---

## Repository Structure

```
github_package/
│
├── charme/                    # Core RL framework
│   ├── env.py                 # RL environment for minor embedding
│   ├── models.py              # GNN-based policy and value networks
│   ├── ppo.py                 # PPO algorithm implementation
│   └── utils.py               # Graph and embedding utilities
│
├── generate_training_data.py  # Generate logical graphs and embeddings
├── train.py                   # Train the RL agent
│
├── training_data/             # Example dataset
│   ├── graph_*.txt             # Logical graph instances
│   └── minorminer_results.pth  # Reference embeddings
│
├── atom/                      # Classical C++ embedding solvers
├── ours/                      # Modified / extended solvers
│
└── README.md
```

---

## Key Features

- **Learning-based Minor Embedding**
  - Models embedding as a sequential assignment task
  - Trained using Proximal Policy Optimization (PPO)

- **Graph Neural Networks**
  - Exploit graph structure of both logical and hardware graphs

- **Hardware-Aware**
  - Designed for Chimera-style quantum annealing topologies
  - Explicit handling of chain length and connectivity constraints

- **Hybrid Pipeline**
  - Python for learning and experimentation
  - C++ for efficient classical baselines

---

## Getting Started

### 1. Generate Training Data (Optional)

This script generates random logical graphs and corresponding embeddings using classical solvers.

```bash
python generate_training_data.py
```

Generated outputs:
- Logical graphs: `training_data/graph_*.txt`
- Reference embeddings: `training_data/minorminer_results.pth`

---

### 2. Train the RL Agent

```bash
python train.py
```

This will:
- Initialize the minor embedding environment
- Train a PPO agent using graph-based observations
- Log training progress and performance metrics

---

## Citation

If you use this code in academic work, please cite the CHARME paper:

```bibtex
@article{Ngo2025_Charme,
author = {Ngo, Hoang and Do, Nguyen and Vu, Minh and Jeter, Tre and Kahveci, Tamer and Thai, My},
title = {CHARME: A Chain-based Reinforcement Learning Approach for the Minor Embedding Problem},
year = {2025},
issue_date = {March 2026},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
volume = {7},
number = {1},
url = {https://doi.org/10.1145/3763244},
doi = {10.1145/3763244},
journal = {ACM Transactions on Quantum Computing},
month = oct,
articleno = {2},
numpages = {28},
keywords = {Minor embedding, quantum annealing, reinforcement learning, optimization}
}
```

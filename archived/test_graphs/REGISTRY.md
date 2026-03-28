# Test Graph Registry

## Selection Syntax

Use a selection string to choose which graphs to benchmark:

| Expression | Meaning |
|------------|---------|
| `"*"` | All graphs |
| `"1-10"` | IDs 1 through 10 (complete graphs) |
| `"1-10, 51-60"` | Complete + special graphs |
| `"1-60"` | All structured graphs (no random) |
| `"1-60, !5"` | All structured except graph 5 (K10) |
| `"100-199"` | All random graphs |
| `"1-199 & !100-199"` | Same as `"1-60"` — `&` and `,` are interchangeable |
| `"51, 52"` | Just Petersen and dodecahedral |

```python
from generate_test_graphs import load_test_graphs
problems = load_test_graphs("1-10, 51-60")  # complete + special
```

## Graph Registry

### 001–010: Complete Graphs

| ID | Name | Nodes | Edges | Density |
|----|------|-------|-------|---------|
|   1 | K4 | 4 | 6 | 1.000 |
|   2 | K5 | 5 | 10 | 1.000 |
|   3 | K6 | 6 | 15 | 1.000 |
|   4 | K8 | 8 | 28 | 1.000 |
|   5 | K10 | 10 | 45 | 1.000 |
|   6 | K12 | 12 | 66 | 1.000 |
|   7 | K15 | 15 | 105 | 1.000 |
### 011–020: Bipartite Graphs

| ID | Name | Nodes | Edges | Density |
|----|------|-------|-------|---------|
|  11 | bipartite_K2_3 | 5 | 6 | 0.600 |
|  12 | bipartite_K3_3 | 6 | 9 | 0.600 |
|  13 | bipartite_K3_4 | 7 | 12 | 0.571 |
|  14 | bipartite_K4_4 | 8 | 16 | 0.571 |
|  15 | bipartite_K4_6 | 10 | 24 | 0.533 |
|  16 | bipartite_K5_5 | 10 | 25 | 0.556 |
### 021–030: Grid Graphs

| ID | Name | Nodes | Edges | Density |
|----|------|-------|-------|---------|
|  21 | grid_2x2 | 4 | 4 | 0.667 |
|  22 | grid_3x3 | 9 | 12 | 0.333 |
|  23 | grid_3x4 | 12 | 17 | 0.258 |
|  24 | grid_4x4 | 16 | 24 | 0.200 |
|  25 | grid_4x6 | 24 | 38 | 0.138 |
|  26 | grid_5x5 | 25 | 40 | 0.133 |
### 031–040: Cycle Graphs

| ID | Name | Nodes | Edges | Density |
|----|------|-------|-------|---------|
|  31 | cycle_5 | 5 | 5 | 0.500 |
|  32 | cycle_8 | 8 | 8 | 0.286 |
|  33 | cycle_10 | 10 | 10 | 0.222 |
|  34 | cycle_15 | 15 | 15 | 0.143 |
|  35 | cycle_20 | 20 | 20 | 0.105 |
|  36 | cycle_30 | 30 | 30 | 0.069 |
### 041–050: Tree Graphs

| ID | Name | Nodes | Edges | Density |
|----|------|-------|-------|---------|
|  41 | tree_r2_d3 | 15 | 14 | 0.133 |
|  42 | tree_r2_d4 | 31 | 30 | 0.065 |
|  43 | tree_r2_d5 | 63 | 62 | 0.032 |
|  44 | tree_r3_d3 | 40 | 39 | 0.050 |
|  45 | tree_r3_d4 | 121 | 120 | 0.017 |
### 051–060: Special Graphs

| ID | Name | Nodes | Edges | Density |
|----|------|-------|-------|---------|
|  51 | petersen | 10 | 15 | 0.333 |
|  52 | dodecahedral | 20 | 30 | 0.158 |
|  53 | icosahedral | 12 | 30 | 0.455 |
### 100–199: Random (Erdős–Rényi) Graphs

| ID | Name | Nodes | Edges | Density |
|----|------|-------|-------|---------|
| 100 | random_n6_d0.2_i0 | 6 | 7 | 0.467 |
| 101 | random_n6_d0.2_i1 | 6 | 4 | 0.267 |
| 102 | random_n6_d0.2_i2 | 6 | 2 | 0.133 |
| 103 | random_n6_d0.3_i0 | 6 | 4 | 0.267 |
| 104 | random_n6_d0.3_i1 | 6 | 4 | 0.267 |
| 105 | random_n6_d0.3_i2 | 6 | 3 | 0.200 |
| 106 | random_n6_d0.5_i0 | 6 | 9 | 0.600 |
| 107 | random_n6_d0.5_i1 | 6 | 10 | 0.667 |
| 108 | random_n6_d0.5_i2 | 6 | 5 | 0.333 |
| 109 | random_n6_d0.7_i0 | 6 | 7 | 0.467 |
| 110 | random_n6_d0.7_i1 | 6 | 9 | 0.600 |
| 111 | random_n6_d0.7_i2 | 6 | 14 | 0.933 |
| 112 | random_n8_d0.2_i0 | 8 | 6 | 0.214 |
| 113 | random_n8_d0.2_i1 | 8 | 3 | 0.107 |
| 114 | random_n8_d0.2_i2 | 8 | 5 | 0.179 |
| 115 | random_n8_d0.3_i0 | 8 | 12 | 0.429 |
| 116 | random_n8_d0.3_i1 | 8 | 6 | 0.214 |
| 117 | random_n8_d0.3_i2 | 8 | 8 | 0.286 |
| 118 | random_n8_d0.5_i0 | 8 | 12 | 0.429 |
| 119 | random_n8_d0.5_i1 | 8 | 16 | 0.571 |
| 120 | random_n8_d0.5_i2 | 8 | 15 | 0.536 |
| 121 | random_n8_d0.7_i0 | 8 | 21 | 0.750 |
| 122 | random_n8_d0.7_i1 | 8 | 19 | 0.679 |
| 123 | random_n8_d0.7_i2 | 8 | 21 | 0.750 |
| 124 | random_n10_d0.2_i0 | 10 | 12 | 0.267 |
| 125 | random_n10_d0.2_i1 | 10 | 6 | 0.133 |
| 126 | random_n10_d0.2_i2 | 10 | 2 | 0.044 |
| 127 | random_n10_d0.3_i0 | 10 | 15 | 0.333 |
| 128 | random_n10_d0.3_i1 | 10 | 18 | 0.400 |
| 129 | random_n10_d0.3_i2 | 10 | 16 | 0.356 |
| 130 | random_n10_d0.5_i0 | 10 | 22 | 0.489 |
| 131 | random_n10_d0.5_i1 | 10 | 25 | 0.556 |
| 132 | random_n10_d0.5_i2 | 10 | 21 | 0.467 |
| 133 | random_n10_d0.7_i0 | 10 | 28 | 0.622 |
| 134 | random_n10_d0.7_i1 | 10 | 29 | 0.644 |
| 135 | random_n10_d0.7_i2 | 10 | 35 | 0.778 |
| 136 | random_n15_d0.2_i0 | 15 | 28 | 0.267 |
| 137 | random_n15_d0.2_i1 | 15 | 19 | 0.181 |
| 138 | random_n15_d0.2_i2 | 15 | 17 | 0.162 |
| 139 | random_n15_d0.3_i0 | 15 | 37 | 0.352 |
| 140 | random_n15_d0.3_i1 | 15 | 30 | 0.286 |
| 141 | random_n15_d0.3_i2 | 15 | 26 | 0.248 |
| 142 | random_n15_d0.5_i0 | 15 | 53 | 0.505 |
| 143 | random_n15_d0.5_i1 | 15 | 51 | 0.486 |
| 144 | random_n15_d0.5_i2 | 15 | 45 | 0.429 |
| 145 | random_n15_d0.7_i0 | 15 | 74 | 0.705 |
| 146 | random_n15_d0.7_i1 | 15 | 70 | 0.667 |
| 147 | random_n15_d0.7_i2 | 15 | 80 | 0.762 |
| 148 | random_n20_d0.2_i0 | 20 | 41 | 0.216 |
| 149 | random_n20_d0.2_i1 | 20 | 36 | 0.190 |
| 150 | random_n20_d0.2_i2 | 20 | 36 | 0.190 |
| 151 | random_n20_d0.3_i0 | 20 | 67 | 0.353 |
| 152 | random_n20_d0.3_i1 | 20 | 51 | 0.268 |
| 153 | random_n20_d0.3_i2 | 20 | 49 | 0.258 |
| 154 | random_n20_d0.5_i0 | 20 | 95 | 0.500 |
| 155 | random_n20_d0.5_i1 | 20 | 96 | 0.505 |
| 156 | random_n20_d0.5_i2 | 20 | 98 | 0.516 |
| 157 | random_n20_d0.7_i0 | 20 | 134 | 0.705 |
| 158 | random_n20_d0.7_i1 | 20 | 122 | 0.642 |
| 159 | random_n20_d0.7_i2 | 20 | 124 | 0.653 |

"""Unified launcher for the neural bake-off families (clean CLI for cluster runs).

  python scripts/train_family.py <gnn-seed|vae|obj> <target> <out.pt> [--device cuda]
"""
import argparse
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("family", choices=["gnn-seed", "vae", "obj", "procrustes"])
    ap.add_argument("target")                      # pegasus_6 | zephyr_4
    ap.add_argument("out")
    ap.add_argument("--data", default="data/learn")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--hidden", type=int, default=160)
    ap.add_argument("--layers", type=int, default=5)
    ap.add_argument("--eval-every", type=int, default=10)
    ap.add_argument("--eval-subset", type=int, default=48)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    common = dict(epochs=a.epochs, hidden=a.hidden, layers=a.layers, device=a.device,
                  eval_every=a.eval_every, eval_subset=a.eval_subset)
    if a.family == "gnn-seed":
        from ember_qc_learn.train import train
        train("gnn-seed", a.data, a.target, a.out, **common)
    elif a.family == "vae":
        from ember_qc_learn.families.vae import train_vae
        train_vae(a.data, target=a.target, out=a.out, **common)
    elif a.family == "obj":
        from ember_qc_learn.families.objective_gnn import train_objective
        train_objective(a.data, target=a.target, out=a.out, **common)
    elif a.family == "procrustes":
        from ember_qc_learn.families.procrustes import train_procrustes
        train_procrustes(a.data, target=a.target, out=a.out, **common)


if __name__ == "__main__":
    main()

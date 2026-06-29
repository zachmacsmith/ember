"""Re-train the P6 Graph-VAE (same hyperparameters as the reported model) while
logging TRAIN and VAL loss per epoch, plus total wall-clock training time, for the
paper's overfitting plot. Writes ckpts/vae_losscurve_p6.json."""
import json
import os
import time

import torch
import dwave_networkx as dnx

from ember_qc_learn.dataset import EmbedDataset
from ember_qc_learn.features import SOURCE_FEATURE_DIM, target_geometry
from ember_qc_learn.models.base import build_model
import ember_qc_learn.models.graph_vae as gv

TARGET, DATA, EPOCHS = "pegasus_6", "data/learn", 80
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.manual_seed(0)

geo = target_geometry(dnx.pegasus_graph(6), TARGET)
tr = EmbedDataset(f"{DATA}/train.jsonl", TARGET, geo=geo)
va = EmbedDataset(f"{DATA}/val.jsonl", TARGET, geo=geo)
cfg = dict(in_dim=SOURCE_FEATURE_DIM, hidden=160, layers=5, conv="sage",
           dropout=0.1, latent_dim=16)                 # matches the reported model
model = build_model("graph-vae", **cfg).to(dev)
loss = gv.VAELoss(beta=0.01, warmup_steps=200)
opt = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-5)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
trl, val = tr.loader(16, shuffle=True), va.loader(32)

hist, t0 = [], time.time()
for ep in range(1, EPOCHS + 1):
    model.train(); tl = 0.0
    for b in trl:
        b = b.to(dev); opt.zero_grad()
        l = loss(model, b, geo); l.backward(); opt.step()
        tl += l.item() * b.num_graphs
    sched.step()
    model.eval(); vl = 0.0
    with torch.no_grad():
        for b in val:
            b = b.to(dev); vl += loss(model, b, geo).item() * b.num_graphs
    hist.append({"epoch": ep, "train_loss": tl / len(tr), "val_loss": vl / len(va)})
elapsed = time.time() - t0

os.makedirs("ckpts", exist_ok=True)
json.dump({"history": hist, "train_seconds": elapsed, "cfg": cfg,
           "epochs": EPOCHS, "device": str(dev), "n_train": len(tr), "n_val": len(va)},
          open("ckpts/vae_losscurve_p6.json", "w"))
print(f"done in {elapsed:.1f}s on {dev}; final train={hist[-1]['train_loss']:.4f} "
      f"val={hist[-1]['val_loss']:.4f}")

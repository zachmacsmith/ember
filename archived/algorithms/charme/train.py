"""Training entrypoint (assembled from CHARME_training.ipynb).

This script mirrors the notebook's training loop, but in a runnable CLI form.
You will likely need to adjust data paths and graph/minorminer loading.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import torch

from charme.env import MinorEmbeddingEnv
from charme.ppo import PPO
import copy


@dataclass
class TrainConfig:
    env_name: str = "CHARME"
    has_continuous_action_space: bool = False
    action_std: float = 0.6
    lr_actor: float = 3e-4
    lr_critic: float = 1e-3
    gamma: float = 0.99
    K_epochs: int = 80
    eps_clip: float = 0.2
    max_training_timesteps: int = int(2e6)
    update_timestep: int = 4000
    log_freq: int = 100
    save_model_freq: int = int(1e5)
    random_seed: int = 0
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


def main(cfg: TrainConfig):
    device = torch.device(cfg.device)

    # ---- ENV SETUP (fill in your real parameters and data loaders) ----
    # The notebook builds the env with many topology params. Example placeholder:
    env = MinorEmbeddingEnv(
        topo_row=8,
        topo_column=8,
        bipart_cell=4,
        goal_dim=1,
        num_nodes=20,
        n_state=1,
        seed=cfg.random_seed,
        degree=3,
        training_size=10,
        mode=0,
    )

    # TODO: load your training graph_list and minorminer_list, then call env.load_graph(...)
    # env.load_graph(graph_list, minorminer_list)

    state_dim = 0  # models read tensors directly from env state dict
    action_dim = env.num_nodes

    ppo_agent = PPO(
        state_dim,
        action_dim,
        cfg.lr_actor,
        cfg.lr_critic,
        cfg.gamma,
        cfg.K_epochs,
        cfg.eps_clip,
        cfg.has_continuous_action_space,
        cfg.action_std,
        device=device,
    )

    print("Starting training...")
    time_step = 0
    i_episode = 0
    nums_done = 0
    saved_res = []

    while time_step <= cfg.max_training_timesteps:
        state = env.reset(mode="batch_change_logical_graph")
        done = False
        current_ep_reward = 0
        current_ep_prob = 0
        count_step = 0

        minorminer_solution_embedding = env.minorminer
        minorminer_solution = env.minorminer_solution
        
        while (not done):
            time_step += 1

            state, action, action_logprob, state_val = ppo_agent.select_action(state, env.mask, env.mask_connected)
            print('Atction:', action)
            state = copy.deepcopy(env.state)
            reward, reward_distance, done = env.step(action.item())

            if done == -1:
                print("Crash....")
                crash_check = True
                ppo_agent.buffer.clear_partial(count_step)
                break

            for k in state.keys():
                if k!='emb_dict':
                    state[k] = state[k].to(device)
                    
            ppo_agent.buffer.states['hw_attr'].append(state['hw_attr'])
            ppo_agent.buffer.states['emb_matrix'].append(state['emb_matrix'])
            ppo_agent.buffer.states['logical_index'].append((env.training_index)%env.training_size)
            ppo_agent.buffer.actions.append(action)
            ppo_agent.buffer.logprobs.append(action_logprob)
            ppo_agent.buffer.state_values.append(state_val)
    
            ppo_agent.buffer.rewards.append(reward)
            ppo_agent.buffer.rewards_distance.append(reward_distance)
            ppo_agent.buffer.is_terminals.append(done)

            current_ep_reward += reward
            current_ep_prob += ppo_agent.max_prob.max()
            if done == 1:
                nums_done = nums_done + 1
                print("minorminer - rl: ", len(minorminer_solution_embedding), "-", len(env.embedding))
                saved_res.append([len(minorminer_solution_embedding), len(env.embedding)])

            if time_step % cfg.update_timestep == 0:
                ppo_agent.update()

        i_episode += 1
        if i_episode % cfg.log_freq == 0:
            print(f"Episode {i_episode}\tTimestep {time_step}\tReward {current_ep_reward:.3f}")

        if time_step % cfg.save_model_freq == 0:
            os.makedirs("checkpoints", exist_ok=True)
            ckpt = os.path.join("checkpoints", f"ppo_{cfg.env_name}_{time_step}.pth")
            ppo_agent.save(ckpt)
            print("Saved:", ckpt)

    print("Finished.")


if __name__ == "__main__":
    main(TrainConfig())

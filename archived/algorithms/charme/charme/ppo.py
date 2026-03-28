"""PPO implementation for CHARME (extracted from CHARME_training.ipynb)."""

from __future__ import annotations

import os
import torch
import torch.nn as nn
from torch.distributions import Categorical, MultivariateNormal, Normal

from .models import ActorCritic

class RolloutBuffer:
    def __init__(self):
        self.actions = []
        self.actions_minor = []
        self.states = {'hw_attr':[], 'emb_matrix':[], 'logical_index':[]}
        self.logprobs = []
        self.rewards = []
        self.rewards_distance = []
        self.state_values = []
        self.is_terminals = []

    def clear_top_20percent(self, memory_size):
        clear_size = int(0.2 * memory_size)
        del self.states['hw_attr'][:clear_size]
        del self.states['emb_matrix'][:clear_size]
        del self.states['logical_index'][:clear_size]
        del self.actions[:clear_size]
        del self.logprobs[:clear_size]
        del self.rewards[:clear_size]
        del self.rewards_distance[:clear_size]
        del self.state_values[:clear_size]
        del self.is_terminals[:clear_size]
    
    def clear_partial(self, memory_size):
        clear_size = len(self.rewards) - memory_size
        del self.states['hw_attr'][clear_size:]
        del self.states['emb_matrix'][clear_size:]
        del self.states['logical_index'][clear_size:]
        del self.actions[clear_size:]
        del self.logprobs[clear_size:]
        del self.rewards[clear_size:]
        del self.rewards_distance[clear_size:]
        del self.state_values[clear_size:]
        del self.is_terminals[clear_size:]
    
    def clear_all(self):
        clear_size = len(self.rewards)
        del self.states['hw_attr'][:clear_size]
        del self.states['emb_matrix'][:clear_size]
        del self.states['logical_index'][:clear_size]
        del self.actions[:clear_size]
        del self.logprobs[:clear_size]
        del self.rewards[:clear_size]
        del self.rewards_distance[:clear_size]
        del self.state_values[:clear_size]
        del self.is_terminals[:clear_size]

    def len(self):
        return len(self.rewards)


class PPO:
    def __init__(self, state_dim, action_dim, lr_actor, lr_critic, gamma, K_epochs,
                 eps_clip, has_continuous_action_space, action_std_init=0.6, device=None) -> None:
        self.has_continuous_action_space = has_continuous_action_space

        if has_continuous_action_space:
            self.action_std = action_std_init

        self.gamma = gamma
        self.eps_clip = eps_clip
        self.K_epochs = K_epochs
        self.max_prob = 0

        self.buffer = RolloutBuffer()
        self.policy = ActorCritic(
            state_dim, action_dim, has_continuous_action_space, action_std_init, device)

        self.optimizer = torch.optim.Adam([
            {'params': self.policy.actor.parameters(), 'lr': lr_actor},
            {'params': self.policy.critic.parameters(), 'lr': lr_critic}
        ])

        self.policy_old = ActorCritic(
            state_dim, action_dim, has_continuous_action_space, action_std_init, device)
        self.policy_old.load_state_dict(self.policy.state_dict())

        self.MseLoss = nn.MSELoss()

    def set_action_std(self, new_action_std):
        if self.has_continuous_action_space:
            self.action_std = new_action_std
            self.policy.set_action_std(new_action_std)
            self.policy_old.set_action_std(new_action_std)

        else:
            print(
                "--------------------------------------------------------------------------------------------")
            print(
                "WARNING : Calling PPO::set_action_std() on discrete action space policy")
            print(
                "--------------------------------------------------------------------------------------------")

    def decay_action_std(self, action_std_decay_rate, min_action_std):
        print("----------------------------------------------------------------------------------------")

        if self.has_continuous_action_space:
            self.action_std = self.action_std - action_std_decay_rate
            self.action_std = round(self.action_std, 4)
            if (self.action_std <= min_action_std):
                self.action_std = min_action_std
                print("setting actor output action_std to min_action_std:", min_action_std)
            else:
                print("setting actor output action_std to:", self.action_std)

        else:
            print(
                "Warning : Calling PPO: decay_action_std() to discrete action space policy")
        print("----------------------------------------------------------------------------------------")

    def select_action(self, state, mask, mask_connected):
        with torch.no_grad():
            pred_action, action_logprob, state_val = self.policy_old.act(state, mask, mask_connected)
            action = pred_action
            self.max_prob = self.policy_old.max_prob

        return state, action, action_logprob, state_val

    def update(self, env, alpha, buffer_index_list):
        total_rewards_ = np.array(total_rewards)
        for index in buffer_index_list:
            batch_start = 0
            buffer_path = 'data/buffer/' + "train_{}".format(run_num_pretrained) + "/PPO_{}.pth".format(index)
            with open(buffer_path, 'rb') as f:
                buffer = pickle.load(f)
                
            # Monte Carlo estimate of returns
            rewards = []
            discounted_reward = 0
            for reward, reward_distance, is_terminal in zip(reversed(buffer.rewards), reversed(buffer.rewards_distance), reversed(buffer.is_terminals)):
                if is_terminal:
                    discounted_reward = 0
                discounted_reward = reward + (self.gamma * discounted_reward)
                rewards.insert(0, discounted_reward + reward_distance)

            # Normalizing the rewards
            rewards = torch.tensor(rewards, dtype=torch.float32).to(device)
            rewards = (rewards - total_rewards_.mean()) / (total_rewards_.std() + 1e-7)
            index = np.array(range(0,buffer.len()))

            old_state_values = torch.squeeze(torch.stack(
                buffer.state_values[batch_start:], dim=0)).detach().to(device)
            advantages = rewards.detach() - old_state_values.detach()
            adv_np = advantages.detach().cpu().numpy()
            adv_np[adv_np < 0] = 0
            nums_nonzero = np.count_nonzero(adv_np)
            if nums_nonzero == 0:
                del rewards
                del old_state_values
                continue
            adv_np = adv_np/adv_np.sum()
            possible_index = np.array(range(0,buffer.len()))
            if time_step > 500:
                selected_index = np.random.choice(possible_index, size=int(min(nums_nonzero, buffer.len())), replace=False, p=adv_np)
            else:
                selected_index = possible_index
            advantages = advantages[selected_index]
            rewards_full = rewards.clone()
            rewards = rewards[selected_index]
            #advantages = (advantages - total_advantages.mean()) / (total_advantages.std() + 1e-8)

            # convert list to tensor
            
            logical_attr = torch.stack([env.fix_state_list[buffer.states['logical_index'][i]]['logical_attr'].clone() 
                                         for i in selected_index]).detach().to(device)
            logical_attr_full = torch.stack([env.fix_state_list[buffer.states['logical_index'][i]]['logical_attr'].clone() 
                                         for i in possible_index]).detach().to(device)
            
            logical_edge_index = torch.stack([env.fix_state_list[buffer.states['logical_index'][i]]['logical_edge_index'].clone()
                                               for i in selected_index]).detach().to(device)
            logical_edge_index_full = torch.stack([env.fix_state_list[buffer.states['logical_index'][i]]['logical_edge_index'].clone()
                                               for i in possible_index]).detach().to(device)

            hw_attr = torch.stack(
                [buffer.states['hw_attr'][i] for i in selected_index]).detach().to(device)
            hw_attr_full = torch.stack(
                [buffer.states['hw_attr'][i] for i in possible_index]).detach().to(device)
                 
            hw_edge_index = torch.stack([env.fix_state_list[buffer.states['logical_index'][i]]['hw_edge_index'].clone() 
                                         for i in selected_index]).detach().to(device)
            hw_edge_index_full = torch.stack([env.fix_state_list[buffer.states['logical_index'][i]]['hw_edge_index'].clone() 
                                         for i in possible_index]).detach().to(device)
                 
            emb_matrix = torch.stack([buffer.states['emb_matrix'][i] for i in selected_index], dim=0).detach().to(device)
            emb_matrix_full = torch.stack([buffer.states['emb_matrix'][i] for i in possible_index], dim=0).detach().to(device)
            
            #emb_dict = self.buffer.states['emb_dict'][batch_start:].copy()

            old_states = {'logical_attr':logical_attr, 'logical_edge_index':logical_edge_index, 
                          'hw_attr':hw_attr, 'hw_edge_index':hw_edge_index, 'emb_matrix':emb_matrix}
            old_states_full = {'logical_attr':logical_attr_full, 'logical_edge_index':logical_edge_index_full, 
                          'hw_attr':hw_attr_full, 'hw_edge_index':hw_edge_index_full, 'emb_matrix':emb_matrix_full}
            old_actions = torch.squeeze(torch.stack(
                buffer.actions[batch_start:], dim=0)[selected_index]).detach().to(device)
            old_logprobs = torch.squeeze(torch.stack(
                buffer.logprobs[batch_start:], dim=0)[selected_index]).detach().to(device)
            
            if alpha == 1:
                advantages = abs(advantages)*(1000**3)
                self.eps_clip = 0.9
            else:
                advantages = advantages
                self.eps_clip = 0.2
            # Optimize policy for K epochs
            for _ in range(self.K_epochs):
                # Evaluating old actions and values
                if alpha == 1:
                    logprobs, state_values, dist_entropy = self.policy.evaluate(
                        old_states, old_actions_minor)
                else:
                    logprobs, state_values, dist_entropy = self.policy.evaluate(
                        old_states, old_actions)
                
                state_values_full = self.policy.critic(old_states_full)
                state_values_full = torch.squeeze(state_values_full)
                # Match state_values tensor dimensions with rewards tensor
                state_values = torch.squeeze(state_values)

                # Finding the ratio (pi_theta / pi_theta_old)
                ratios = torch.exp(logprobs - old_logprobs.detach())

                # Finding Surrogates Loss
                surr1 = ratios * advantages
                surr2 = torch.clamp(ratios, 1 - self.eps_clip,
                                    1 + self.eps_clip) * advantages

                # Finall loss of clipped objective PPO
                loss = - torch.min(surr1, surr2) + 0.5 * self.MseLoss(state_values_full, rewards_full)
                #+ 0.5*self.MseLoss(old_actions.to(float),old_actions_minor.to(float)) - 0.004 * dist_entropy

                # take gradient step
                self.optimizer.zero_grad()
                loss.mean().backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
                self.optimizer.step()
                
            del rewards
            del logical_attr
            del logical_edge_index
            del hw_attr
            del hw_edge_index
            del emb_matrix
            del old_actions
            del old_logprobs
            del old_state_values
            buffer.clear_all()
                #print(loss.mean())

            # Copy new weights into old policy
            self.policy_old.load_state_dict(self.policy.state_dict())

        # Clear buffer - Don't need if you run with Her
        # if self.buffer.len()>=1e12:
        #     self.buffer.clear_top_20percent()

    def save(self, checkpoint_path):
        torch.save(self.policy_old.state_dict(), checkpoint_path)

    def load(self, checkpoint_path):
        self.policy_old.load_state_dict(torch.load(
            checkpoint_path, map_location=lambda storage, loc: storage))

        self.policy.load_state_dict(torch.load(
            checkpoint_path, map_location=lambda storage, loc: storage))

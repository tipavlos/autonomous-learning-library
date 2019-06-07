import torch
from all.environments import State
from .abstract import Agent

class VPG(Agent):
    def __init__(
            self,
            features,
            v,
            policy,
            gamma=0.99,
            n_episodes=1
    ):
        self.features = features
        self.v = v
        self.policy = policy
        self.gamma = gamma
        self.n_episodes = n_episodes
        self._trajectories = []
        self._features = []
        self._rewards = []

    def act(self, state, reward):
        if not self._features:
            return self._initial(state)
        if not state.done:
            return self._act(state, reward)
        return self._terminal(reward)

    def _initial(self, state):
        features = self.features(state)
        self._features = [features.features]
        return self.policy(features)

    def _act(self, state, reward):
        features = self.features(state)
        self._features.append(features.features)
        self._rewards.append(reward)
        return self.policy(features)

    def _terminal(self, reward):
        self._rewards.append(reward)
        features = torch.cat(self._features)
        rewards = torch.tensor(self._rewards, device=features.device)
        self._trajectories.append((features, rewards))
        self._features = []
        self._rewards = []

        if len(self._trajectories) >= self.n_episodes:
            self._train()

    def _train(self):
        advantages = torch.cat([
            self._compute_advantages(features, rewards)
            for (features, rewards)
            in self._trajectories
        ])
        self.v.reinforce(advantages, retain_graph=True)
        self.policy.reinforce(advantages)
        self.features.reinforce()
        self._trajectories = []

    def _compute_advantages(self, features, rewards):
        returns = self._compute_discounted_returns(rewards)
        values = self.v(State(features))
        return returns - values

    def _compute_discounted_returns(self, rewards):
        returns = rewards.clone()
        t = len(returns) - 1
        discounted_return = 0
        for reward in torch.flip(rewards, dims=(0,)):
            discounted_return = reward + self.gamma * discounted_return
            returns[t] = discounted_return
            t -= 1
        return returns
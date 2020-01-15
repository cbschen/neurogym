#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Delay Match to sample

"""
from __future__ import division

import numpy as np
from gym import spaces
from neurogym.ops import tasktools
import neurogym as ngym


class DelayedMatchToSample(ngym.EpochEnv):
    metadata = {
        'paper_link': 'https://www.jneurosci.org/content/jneuro/16/16/5154.full.pdf',
        'paper_name': '''Neural Mechanisms of Visual Working Memory 
        in Prefrontal Cortex of the Macaque''',
        'default_timing': {
            'fixation': ('constant', 300),
            'sample': ('constant', 500),
            'delay': ('constant', 1000),
            'test': ('constant', 500),
            'decision': ('constant', 900)},
    }

    def __init__(self, dt=100, timing=None):
        super().__init__(dt=dt, timing=timing)
        # TODO: Code a continuous space version
        # Actions ('FIXATE', 'MATCH', 'NONMATCH')
        self.actions = [0, -1, 1]
        self.choices = [1, 2]
        # Input noise
        self.sigma = np.sqrt(2*100*0.01)
        self.sigma_dt = self.sigma/np.sqrt(self.dt)

        # Rewards
        self.R_ABORTED = -0.1
        self.R_CORRECT = +1.
        self.R_FAIL = 0.
        self.R_MISS = 0.
        self.abort = False

        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(3,),
                                            dtype=np.float32)

    def new_trial(self, **kwargs):
        # ---------------------------------------------------------------------
        # Trial
        # ---------------------------------------------------------------------
        self.trial = {
            'ground_truth': self.rng.choice(self.choices),
            'sample': self.rng.choice([1, 2]),
        }
        self.trial.update(kwargs)

        ground_truth = self.trial['ground_truth']
        sample = self.trial['sample']

        test = sample if ground_truth == 1 else 3 - sample
        self.trial['test'] = test
        # ---------------------------------------------------------------------
        # Epochs
        # ---------------------------------------------------------------------
        self.add_epoch('fixation', after=0)
        self.add_epoch('sample', after='fixation')
        self.add_epoch('delay', after='sample')
        self.add_epoch('test', after='delay')
        self.add_epoch('decision', after='test', last_epoch=True)

        self.set_ob('fixation', [1, 0, 0])
        ob = self.view_ob('sample')
        ob[:, 0] = 1
        ob[:, sample] = 1
        ob[:, 1:] += np.random.randn(ob.shape[0], 2) * self.sigma_dt

        ob = self.view_ob('test')
        ob[:, 0] = 1
        ob[:, test] = 1
        ob[:, 1:] += np.random.randn(ob.shape[0], 2) * self.sigma_dt

        self.set_ob('delay', [1, 0, 0])

        self.set_groundtruth('decision', ground_truth)

    def _step(self, action):
        new_trial = False
        reward = 0

        obs = self.obs_now
        gt = self.gt_now

        if self.in_epoch('fixation'):
            if action != 0:
                new_trial = self.abort
                reward = self.R_ABORTED
        elif self.in_epoch('decision'):
            if action != 0:
                new_trial = True
                if action == gt:
                    reward = self.R_CORRECT
                else:
                    reward = self.R_FAIL

        return obs, reward, False, {'new_trial': new_trial, 'gt': gt}

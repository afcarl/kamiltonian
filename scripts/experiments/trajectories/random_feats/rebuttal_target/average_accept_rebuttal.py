import os

from kmc.tools.Log import logger
import numpy as np
from scripts.experiments.trajectories.independent_jobs_classes.random_feats.RebuttalTrajectoryJob import RebuttalTrajectoryJob
from scripts.experiments.trajectories.tools import process


modulename = __file__.split(os.sep)[-1].split('.')[-2]

if __name__ == "__main__":
    logger.setLevel(10)
    sigma_q = 1.
    sigma_p = 1.
    Ds = np.sort(2 ** np.arange(6))[::-1]
    Ns = np.sort([100, 200, 500, 1000, 2000, 5000, 10000, 16000])[::-1]
    
    num_repetitions = 10
    num_steps = 10
    max_steps = 100
    step_size = .1
    
    alpha0 = 0.6
    lmbda0 = 0.000048
    
    job_generator = lambda D, N, m : RebuttalTrajectoryJob(N, D, m, sigma_p,
                                                     num_steps, step_size,
                                                     alpha0, lmbda0, max_steps,
                                                     learn_parameters=False)
    
    process(modulename, job_generator, Ds, Ns, num_repetitions, num_steps,
            step_size, max_steps, compute_local=False)

from abc import abstractmethod
import os

from kmc.hamiltonian.hamiltonian import compute_log_accept_pr
from kmc.hamiltonian.leapfrog import leapfrog, leapfrog_no_storing
from kmc.score_matching.lite.estimator import LiteEstimatorGaussian
from kmc.score_matching.lite.gaussian_rkhs import score_matching_sym
from kmc.score_matching.random_feats.estimator import RandomFeatsEstimator
from kmc.score_matching.random_feats.gaussian_rkhs_xvalidation import select_sigma_lambda_cma
from kmc.tools.Log import logger
import numpy as np
from scripts.experiments.mcmc.independent_job_classes.HMCJob import HMCJob,\
    HMCJobResultAggregator
from scripts.tools.plotting import evaluate_gradient_grid, plot_array,\
    evaluate_density_grid
from kmc.densities.gaussian import log_gaussian_pdf


splitted = __file__.split(os.sep)
idx = splitted.index('kamiltonian')
project_path = os.sep.join(splitted[:(idx + 1)])

temp = 0

class DummyHABCTarget(object):
    def __init__(self, mu=None, L=None, prior=None):
        self.mu = mu
        self.L = L
        self.prior = prior
    
    def set_up(self):
        pass
        
    def grad(self, theta):
        log_lik = log_gaussian_pdf(theta, self.mu, self.L, is_cholesky=True,
                                compute_grad=True)
        log_prior = self.prior.grad(theta)
        return log_lik + log_prior
    
    def log_pdf(self, theta):
        # should not happen, this is
        assert False

class HABCJob(HMCJob):
    def __init__(self, abc_target, momentum,
                 num_iterations, start,
                 num_steps_min=10, num_steps_max=100, step_size_min=0.05,
                 step_size_max=0.3, momentum_seed=0,
                 statistics={}, num_warmup=500, thin_step=1):
        
        HMCJob.__init__(self, abc_target, momentum,
                        num_iterations, start,
                        num_steps_min, num_steps_max, step_size_min,
                        step_size_max, momentum_seed, statistics, num_warmup, thin_step)
        
        self.aggregator = HABCJobResultAggregator()

    @abstractmethod
    def set_up(self):
        # remember orginal abc target for later
        self.abc_target = self.target
        
        HMCJob.set_up(self)

    @abstractmethod
    def propose(self, current, current_log_pdf, samples, accepted):
        # sample pseudo data to fit conditional model
        pseudo_datas = np.zeros((self.abc_target.n_lik_samples, self.D))
        for i in range(len(pseudo_datas)):
            pseudo_datas[i] = self.abc_target.simulator(current)
        
        # fit Gaussian, add ridge on diagonal for the epsilon likelihood kernel
        mu = np.mean(pseudo_datas, 0)
        Sigma = np.cov(pseudo_datas) + np.eye(len(mu))*(self.abc_target.epsilon**2)
        L = np.linalg.cholesky(Sigma)
        
        self.target = DummyHABCTarget(mu, L, self.abc_target.prior)
        
        # use normal HMC mechanics from here
        return HMCJob.propose(self, current, current_log_pdf, samples, accepted)
    
    @abstractmethod
    def accept_prob_log_pdf(self, current, q, p0_log_pdf, p_log_pdf, current_log_pdf=None):
        # potentially re-use log_pdf of last accepted state
        if current_log_pdf is None:
            current_log_pdf = -np.inf
        
        # same as super-class, but with original target
        habc_target = self.target
        self.target = self.abc_target
        
        acc_prob, log_pdf_q = HMCJob.accept_prob_log_pdf(self, current, q, p0_log_pdf, p_log_pdf, current_log_pdf)
        
        # restore target
        self.target = habc_target
    
#         return acc_prob, log_pdf_q
        return 1.0, log_pdf_q
    
    @abstractmethod
    def get_parameter_fname_suffix(self):
        return "HABC_" + HMCJob.get_parameter_fname_suffix(self)[4:] 
    

class HABCJobResultAggregator(HMCJobResultAggregator):
    def __init__(self):
        HMCJobResultAggregator.__init__(self)
        
    @abstractmethod
    def fire_and_forget_result_strings(self):
        strings = HMCJobResultAggregator.fire_and_forget_result_strings(self)
        
        return [str(self.result.D)] + strings
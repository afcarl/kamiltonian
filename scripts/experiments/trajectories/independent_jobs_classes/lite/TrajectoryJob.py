from abc import abstractmethod

from independent_jobs.jobs.IndependentJob import IndependentJob

from kmc.densities.gaussian import sample_gaussian, log_gaussian_pdf
from kmc.hamiltonian.hamiltonian import compute_log_accept_pr, \
    compute_log_det_trajectory
from kmc.hamiltonian.leapfrog import leapfrog
from kmc.score_matching.kernel.kernels import gaussian_kernel,\
    gaussian_kernel_grad
from kmc.score_matching.lite.estimator import log_pdf_estimate_grad
from kmc.score_matching.lite.gaussian_rkhs import _compute_b_sym, _compute_C_sym,\
    score_matching_sym
from kmc.score_matching.lite.gaussian_rkhs_xvalidation import select_sigma_grid
from kmc.tools.Log import logger
import numpy as np
from scripts.experiments.trajectories.independent_jobs_classes.TrajectoryJobResult import TrajectoryJobResult
from scripts.experiments.trajectories.independent_jobs_classes.TrajectoryJobResultAggregator import TrajectoryJobResultAggregator


class TrajectoryJob(IndependentJob):
    def __init__(self,
                 N, D, lmbda, sigma_p, num_steps, step_size, max_steps=None):
        IndependentJob.__init__(self, TrajectoryJobResultAggregator())
        
        self.N = N
        self.D = D
        self.lmbda = lmbda
        self.sigma_p = sigma_p
        self.num_steps = num_steps
        self.step_size = step_size
        self.max_steps = max_steps
    
    @abstractmethod
    def set_up(self):
        raise NotImplementedError()
    
    def compute_trajectory(self, random_start_state=None):
        logger.debug("Entering")
        
        if random_start_state is not None:
            np.random.set_state(random_start_state)
        else:
            random_start_state = np.random.get_state()
        
        # momentum
        L_p = np.linalg.cholesky(np.eye(self.D) * self.sigma_p)
        self.logp = lambda x: log_gaussian_pdf(x, Sigma=L_p, compute_grad=False, is_cholesky=True)
        self.dlogp = lambda x: log_gaussian_pdf(x, Sigma=L_p, compute_grad=True, is_cholesky=True)
        self.p_sample = lambda: sample_gaussian(N=1, mu=np.zeros(self.D), Sigma=L_p, is_cholesky=True)[0]
        self.p_sample = lambda: sample_gaussian(N=1, mu=np.zeros(self.D), Sigma=L_p, is_cholesky=True)[0]
        
        # set up target and momentum densities and gradients
        self.set_up()
        
        logger.info("Learning kernel bandwidth")
        sigma = select_sigma_grid(self.Z, lmbda=self.lmbda, log2_sigma_max=15)
        logger.info("Using lmbda=%.2f, sigma: %.2f" % (self.lmbda, sigma))
        
        logger.info("Computing kernel matrix")
        K = gaussian_kernel(self.Z, sigma=sigma)
        
        logger.info("Estimate density in RKHS")
        b = _compute_b_sym(self.Z, K, sigma)
        C = _compute_C_sym(self.Z, K, sigma)
        a = score_matching_sym(self.Z, sigma, self.lmbda, K, b, C)
        
#         logger.info("Computing objective function")
#         J = _objective_sym(Z, sigma, self.lmbda, a, K, b, C)
#         J_xval = np.mean(xvalidate(Z, 5, sigma, self.lmbda, K))
#         logger.info("N=%d, sigma: %.2f, lambda: %.2f, J(a)=%.2f, XJ(a)=%.2f" % \
#                 (self.N, sigma, self.lmbda, J, J_xval))
        
        kernel_grad = lambda x, X = None: gaussian_kernel_grad(x, X, sigma)
        dlogq_est = lambda x: log_pdf_estimate_grad(x, a, self.Z, kernel_grad)
        
        
        logger.info("Simulating trajectory for L=%d steps of size %.2f" % \
                     (self.num_steps, self.step_size))
        # starting state
        p0 = self.p_sample()
        q0 = self.q_sample()
        
        Qs, Ps = leapfrog(q0, self.dlogq, p0, self.dlogp, self.step_size, self.num_steps, self.max_steps)
        
        # run second integrator for same amount of steps
        steps_taken = len(Qs)
        logger.info("%d steps taken" % steps_taken)
        Qs_est, Ps_est = leapfrog(q0, dlogq_est, p0, self.dlogp, self.step_size, steps_taken)
        
        logger.info("Computing average acceptance probabilities")
        log_acc = compute_log_accept_pr(q0, p0, Qs, Ps, self.logq, self.logp)
        log_acc_est = compute_log_accept_pr(q0, p0, Qs_est, Ps_est, self.logq, self.logp)
        acc_mean = np.mean(np.exp(log_acc))
        acc_est_mean = np.mean(np.exp(log_acc_est))
        
        logger.info("Computing average volumes")
        log_det = compute_log_det_trajectory(Qs, Ps)
        log_det_est = compute_log_det_trajectory(Qs_est, Ps_est)
        
        logger.info("Average acceptance prob: %.2f, %.2f" % (acc_mean, acc_est_mean))
        logger.info("Log-determinant: %.2f, %.2f" % (log_det, log_det_est))
        
        logger.debug("Leaving")
        return acc_mean, acc_est_mean, log_det, log_det_est, steps_taken, random_start_state
    
    def compute(self):
        logger.debug("Entering")
        random_start_state = np.random.get_state()
        
        acc_mean, acc_est_mean, log_det, log_det_est, steps_taken, random_start_state = \
            self.compute_trajectory(random_start_state)
        
        logger.info("Submitting results to aggregator")
        result = TrajectoryJobResult(acc_mean, acc_est_mean, log_det,
                                     log_det_est, steps_taken, random_start_state)
        self.aggregator.submit_result(result)
        
        logger.debug("Leaving")

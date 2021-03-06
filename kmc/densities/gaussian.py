from scipy.linalg import solve_triangular
from scipy.stats._continuous_distns import chi2

import numpy as np


def log_gaussian_pdf(x, mu=None, Sigma=None, is_cholesky=False, compute_grad=False):
    if mu is None:
        mu = np.zeros(len(x))
    if Sigma is None:
        Sigma = np.eye(len(mu))
    
    if is_cholesky is False:
        L = np.linalg.cholesky(Sigma)
    else:
        L = Sigma
    
    assert len(x) == Sigma.shape[0]
    assert len(x) == Sigma.shape[1]
    assert len(x) == len(mu)
    
    # solve y=K^(-1)x = L^(-T)L^(-1)x
    x = np.array(x - mu)
    y = solve_triangular(L, x.T, lower=True)
    y = solve_triangular(L.T, y, lower=False)
    
    if not compute_grad:
        log_determinant_part = -np.sum(np.log(np.diag(L)))
        quadratic_part = -0.5 * x.dot(y)
        const_part = -0.5 * len(L) * np.log(2 * np.pi)
        
        return const_part + log_determinant_part + quadratic_part
    else:
        return -y

def sample_gaussian(N, mu=np.zeros(2), Sigma=np.eye(2), is_cholesky=False):
    D = len(mu)
    assert len(mu.shape) == 1
    assert len(Sigma.shape) == 2
    assert D == Sigma.shape[0]
    assert D == Sigma.shape[1]
    
    if is_cholesky is False:
        L = np.linalg.cholesky(Sigma)
    else:
        L = Sigma
    
    return L.dot(np.random.randn(D, N)).T + mu

def emp_quantiles(X, mu=np.zeros(2), Sigma=np.eye(2),
                  quantiles=np.arange(0.1, 1, 0.1)):
    D = X.shape[1]
    
    # need inverse chi2 cdf with self.dimension degrees of freedom
    chi2_instance = chi2(D)
    cutoffs = chi2_instance.isf(1 - quantiles)
    # whitening
    D, U = np.linalg.eig(Sigma)
    D = D ** (-0.5)
    W = (np.diag(D).dot(U.T).dot((X - mu).T)).T
    norms_squared = np.array([np.linalg.norm(w) ** 2 for w in W])
    results = np.zeros([len(quantiles)])
    for jj in range(0, len(quantiles)):
        results[jj] = np.mean(norms_squared < cutoffs[jj])
    return results

class IsotropicZeroMeanGaussian(object):
    def __init__(self, sigma=1., D=1):
        self.sigma = sigma
        self.D = D
    
    def log_pdf(self, x):
        D = len(x)
        const_part = -0.5 * D * np.log(2 * np.pi)
        quadratic_part = -np.dot(x, x) / (2 * (self.sigma ** 2))
        log_determinant_part = -D * np.log(self.sigma)
        return const_part + log_determinant_part + quadratic_part
    
    def grad(self, x):
        return -x / (self.sigma ** 2)
    
    def sample(self):
        return np.random.randn(self.D) * self.sigma
        

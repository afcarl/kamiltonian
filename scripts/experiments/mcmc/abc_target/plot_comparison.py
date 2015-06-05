from glob import glob
from matplotlib.lines import Line2D
import pickle
import seaborn as sns
sns.set_style("white")
sns.set_style("whitegrid")


from kmc.tools.latex_plot_init import plt

from kmc.tools.Log import logger
from kmc.tools.convergence_stats import autocorr
import numpy as np


if __name__ == "__main__":
    logger.setLevel(10)
    
    warmup = 200
    num_samples = 2000
    num_Ns = 3
    Ns = np.round(np.linspace(1, num_samples, num_Ns)).astype(int)
    num_repetitions = 10
    
    benchmark_samples = np.load("ground_truth/benchmark_samples.arr")

    fnames_kmc = glob('lite/KMC_N=1000_D=10_ground_truth_iterations=5200*.pkl')[:num_repetitions]
    fnames_rw = glob('rw/RW_D=10_ground_truth_iterations=5200*.pkl')[:num_repetitions]
    fnames_habc = glob('habc/HABC_D=10_ground_truth_iterations=2200*.pkl')[:num_repetitions]
    
    colors = [
              "b",
              "m",
            "y",
              ]
    
    # two figures: autocorrelation and mean estimation
    f_acor, ax_acor = plt.subplots()
    f_mean, ax_kde = plt.subplots()
    
    for alg_idx, fnames in enumerate([
                   fnames_kmc,
                   fnames_rw,
                   fnames_habc,
                   ]):
        
        if len(fnames) <= 0:
            exit()
    
        acorrs = np.zeros((len(fnames), 100))
        for i, fname in enumerate(fnames):
            logger.info("%s" % fname)
            with open(fname) as f:
                result = pickle.load(f)
                
            # print some summary stats
            accepted = result.accepted
            samples = result.samples
            avg_ess = result.posterior_statistics["avg_ess"]
            min_ess = result.posterior_statistics["min_ess"]
            
            time = result.time_taken_sampling
            time_set_up = result.time_taken_set_up
        
            logger.info("Average acceptance probability: %.2f" % np.mean(accepted))
            logger.info("Average ESS: %.2f" % avg_ess)
            logger.info("Minimum ESS: %.2f" % min_ess)
            total_time_s = time + time_set_up
            total_time_m = total_time_s / 60
            logger.info("Total time: %.2f sec, %.2f min" % (total_time_s, total_time_m))
            logger.info("Average ESS/s: %.2f" % (avg_ess / total_time_s))
            logger.info("Minimum ESS/s: %.2f" % (min_ess / total_time_s))
            
            # KDE
            if i==0:
                sns.kdeplot(samples[:,0], shade=True, ax = ax_kde, color=colors[alg_idx]);
                ax_kde.set_xlabel(r"$\theta_0$")
                ax_kde.set_ylabel(r"$p(\theta_0)$")
                
#                 # plot mean
#                 m = np.mean(samples[:,0])
#                 sns.plt.plot([m,m], [0,.7], color=colors[alg_idx])
                
                ax_kde.grid(True)
                plt.sca(ax_kde)
                plt.savefig("abc_target_marginal0.pdf", bbox_inches="tight")
                
            # compute autocorrelation of the first dimension
            acorrs[i,:] = autocorr(samples[:, 0])[:100]
        
        med =  np.median(acorrs, 0)
        lower =  np.percentile(acorrs, 20, 0)
        upper = np.percentile(acorrs, 80, 0)
        
        ax_acor.plot(med, "-", color=colors[alg_idx])
        ax_acor.plot(lower, '--', color=colors[alg_idx])
        ax_acor.plot(upper, '--', color=colors[alg_idx])
           
    ax_acor.set_xlabel("Lag")
    ax_acor.set_ylabel("Autocorrelation")
    line1 = Line2D([0, 0], [0, 0], color=colors[0])
    line2 = Line2D([0, 0], [0, 0], color=colors[1])
    line3 = Line2D([0, 0], [0, 0], color=colors[2])
    ax_acor.legend((line1, line2, line3), ["KMC", "RW","HABC"])
    ax_acor.grid(True)
    plt.sca(ax_acor)
    plt.savefig("abc_target_autocorr.pdf", bbox_inches="tight")
    plt.show()

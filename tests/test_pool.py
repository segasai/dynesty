import numpy as np
import pytest
import dynesty
import multiprocessing as mp
import dynesty.pool as dypool
from utils import get_rstate, get_printing
"""
Run a series of basic tests to check whether anything huge is broken.

"""

nlive = 1000
printing = get_printing()

ndim = 2
gau_s = 0.01


def loglike_gau(x):
    return (-0.5 * np.log(2 * np.pi) * ndim - np.log(gau_s) * ndim -
            0.5 * np.sum((x - 0.5)**2) / gau_s**2)


def prior_transform_gau(x):
    return x


# EGGBOX
# see 1306.2144
def loglike_egg(x):
    logl = ((2 + np.cos(x[0] / 2) * np.cos(x[1] / 2))**5)
    return logl


def prior_transform_egg(x):
    return x * 10 * np.pi


LOGZ_TRUTH_GAU = 0
LOGZ_TRUTH_EGG = 235.856


def test_pool():
    # test pool on egg problem
    rstate = get_rstate()

    # i specify large queue_size here, otherwise it is too slow
    with dypool.Pool(2, loglike_egg, prior_transform_egg) as pool:
        sampler = dynesty.NestedSampler(pool.loglike,
                                        pool.prior_transform,
                                        ndim,
                                        nlive=nlive,
                                        pool=pool,
                                        queue_size=100,
                                        rstate=rstate)
        sampler.run_nested(dlogz=0.1, print_progress=printing)

        assert (abs(LOGZ_TRUTH_EGG - sampler.results['logz'][-1]) <
                5. * sampler.results['logzerr'][-1])


def test_pool_x():
    # check without specifying queue_size
    rstate = get_rstate()

    with dypool.Pool(2, loglike_egg, prior_transform_egg) as pool:
        sampler = dynesty.NestedSampler(pool.loglike,
                                        pool.prior_transform,
                                        ndim,
                                        nlive=50,
                                        pool=pool,
                                        rstate=rstate)
        sampler.run_nested(print_progress=printing, maxiter=100)

        assert (abs(LOGZ_TRUTH_EGG - sampler.results['logz'][-1]) <
                5. * sampler.results['logzerr'][-1])


def test_pool_dynamic():
    # test pool on gau problem
    # i specify large queue_size here, otherwise it is too slow
    rstate = get_rstate()

    with dypool.Pool(2, loglike_gau, prior_transform_gau) as pool:
        sampler = dynesty.DynamicNestedSampler(pool.loglike,
                                               pool.prior_transform,
                                               ndim,
                                               nlive=nlive,
                                               pool=pool,
                                               queue_size=100,
                                               rstate=rstate)
        sampler.run_nested(dlogz_init=1, print_progress=printing)

        assert (abs(LOGZ_TRUTH_GAU - sampler.results['logz'][-1]) <
                5. * sampler.results['logzerr'][-1])


def loglike_gau_args(x, y, z=None):
    return (-0.5 * np.log(2 * np.pi) * ndim - np.log(gau_s) * ndim -
            0.5 * np.sum((x - 0.5)**2) / gau_s**2) + y + z


def prior_transform_gau_args(x, y, z=None):
    return x + y + z


def test_pool_args():
    # test pool on gau problem
    # i specify large queue_size here, otherwise it is too slow
    rstate = get_rstate()

    with dypool.Pool(2,
                     loglike_gau_args,
                     prior_transform_gau_args,
                     logl_args=(0, ),
                     ptform_args=(0, ),
                     logl_kwargs=dict(z=0),
                     ptform_kwargs=dict(z=0)) as pool:
        sampler = dynesty.DynamicNestedSampler(pool.loglike,
                                               pool.prior_transform,
                                               ndim,
                                               nlive=nlive,
                                               pool=pool,
                                               queue_size=100,
                                               rstate=rstate)
        sampler.run_nested(maxiter=300, print_progress=printing)

        assert (abs(LOGZ_TRUTH_GAU - sampler.results['logz'][-1]) <
                5. * sampler.results['logzerr'][-1])

        # to ensure we get coverage
        pool.close()
        pool.join()


@pytest.mark.parametrize('sample', ['slice', 'rwalk', 'rslice'])
def test_pool_samplers(sample):
    # this is to test how the samplers are dealing with queue_size>1
    rstate = get_rstate()

    with mp.Pool(2) as pool:
        sampler = dynesty.NestedSampler(loglike_gau,
                                        prior_transform_gau,
                                        ndim,
                                        nlive=nlive,
                                        sample=sample,
                                        pool=pool,
                                        queue_size=10,
                                        rstate=rstate)
        sampler.run_nested(print_progress=printing)
        assert (abs(LOGZ_TRUTH_GAU - sampler.results['logz'][-1]) <
                5. * sampler.results['logzerr'][-1])


POOL_KW = ['prior_transform', 'loglikelihood', 'propose_point', 'update_bound']


@pytest.mark.parametrize('func', POOL_KW)
def test_usepool(func):
    # test all the use_pool options, toggle them one by one
    rstate = get_rstate()
    use_pool = {}
    for k in POOL_KW:
        use_pool[k] = False
    use_pool[func] = True

    with mp.Pool(2) as pool:
        sampler = dynesty.DynamicNestedSampler(loglike_gau,
                                               prior_transform_gau,
                                               ndim,
                                               nlive=nlive,
                                               rstate=rstate,
                                               use_pool=use_pool,
                                               pool=pool,
                                               queue_size=100)
        sampler.run_nested(maxiter=10000, print_progress=printing)

import numpy as np
import pytest
import dynesty
import pickle
from scipy import linalg
import dynesty.utils as dyutil
from multiprocessing import Pool
import itertools
from utils import get_rstate, get_printing, NullContextManager
"""
Run a series of basic tests changing various things like
maxcall options and potentially other things
"""

printing = get_printing()

nlive = 100

size = 10  # box size


def loglike(x):
    return -0.5 * np.sum(x**2)


def loglike_inf(x):
    r2 = np.sum(x**2)
    if r2 > size * size or np.abs(x[0]) < 0.1:
        return -np.inf
    return -0.5 * r2


class MyException(Exception):
    pass


def loglike_exc(x):
    r2 = np.sum(x**2)
    if r2 < 0.1:
        raise MyException('ooops')
    return -0.5 * r2


def prior_transform(x):
    return (2 * x - 1) * size


def test_maxcall():
    # test of maxcall functionality
    ndim = 2
    rstate = get_rstate()
    sampler = dynesty.NestedSampler(loglike,
                                    prior_transform,
                                    ndim,
                                    nlive=nlive,
                                    rstate=rstate)
    sampler.run_nested(dlogz=1, maxcall=1000, print_progress=printing)

    sampler = dynesty.DynamicNestedSampler(loglike,
                                           prior_transform,
                                           ndim,
                                           nlive=nlive,
                                           rstate=rstate)
    sampler.run_nested(dlogz_init=1, maxcall=1000, print_progress=printing)


def test_n_effective_deprecation():
    # test deprecation of n_effective and n_effective_init
    ndim = 2
    rstate = get_rstate()

    sampler = dynesty.NestedSampler(loglike,
                                    prior_transform,
                                    ndim,
                                    nlive=nlive,
                                    rstate=rstate)
    with pytest.deprecated_call():
        sampler.run_nested(dlogz=1, maxcall=10, n_effective=10)

    sampler = dynesty.DynamicNestedSampler(loglike,
                                           prior_transform,
                                           ndim,
                                           nlive=nlive,
                                           rstate=rstate)

    sample_generator = sampler.sample_initial(n_effective=10)
    with pytest.deprecated_call():
        next(sample_generator)

    with pytest.deprecated_call():
        sampler.run_nested(dlogz_init=1, maxcall=10, n_effective_init=10)


@pytest.mark.parametrize('dynamic,with_pool',
                         itertools.product([True, False], [True, False]))
def test_pickle(dynamic, with_pool):
    # test of pickling functionality
    ndim = 2
    rstate = get_rstate()

    with (NullContextManager() if not with_pool else Pool(2)) as pool:
        if with_pool:
            kw = dict(pool=pool, queue_size=100)
        else:
            kw = {}

        if dynamic:
            sampler = dynesty.DynamicNestedSampler(loglike,
                                                   prior_transform,
                                                   ndim,
                                                   nlive=nlive,
                                                   rstate=rstate,
                                                   **kw)
        else:
            sampler = dynesty.NestedSampler(loglike,
                                            prior_transform,
                                            ndim,
                                            nlive=nlive,
                                            rstate=rstate,
                                            **kw)
        sampler.run_nested(print_progress=printing, maxiter=100)
        # i do it twice as there were issues previously
        # with incorrect pool restoring
        S = pickle.dumps(sampler)
        sampler = pickle.loads(S)
        S = pickle.dumps(sampler)
        sampler = pickle.loads(S)
        sampler.run_nested(print_progress=printing, maxiter=100)


def test_inf():
    # Test of logl that returns -inf
    ndim = 2
    rstate = get_rstate()
    sampler = dynesty.NestedSampler(loglike_inf,
                                    prior_transform,
                                    ndim,
                                    nlive=nlive,
                                    rstate=rstate)
    sampler.run_nested(print_progress=printing)

    sampler = dynesty.DynamicNestedSampler(loglike_inf,
                                           prior_transform,
                                           ndim,
                                           nlive=nlive,
                                           rstate=rstate)
    sampler.run_nested(dlogz_init=1, print_progress=printing)


def test_unravel():
    # test unravel_run
    ndim = 2
    rstate = get_rstate()
    sampler = dynesty.NestedSampler(loglike,
                                    prior_transform,
                                    ndim,
                                    nlive=nlive,
                                    rstate=rstate)
    sampler.run_nested(print_progress=printing)
    dyutil.unravel_run(sampler.results)

    sampler = dynesty.DynamicNestedSampler(loglike,
                                           prior_transform,
                                           ndim,
                                           nlive=nlive,
                                           rstate=rstate)
    sampler.run_nested(dlogz_init=1, maxcall=1000, print_progress=printing)
    dyutil.unravel_run(sampler.results)
    logps = sampler.results.logl
    dyutil.reweight_run(sampler.results, logps / 4.)


def test_livepoints():
    # Test the providing of initial live-points to the sampler
    ndim = 2
    rstate = get_rstate()
    live_u = rstate.uniform(size=(nlive, ndim))
    live_v = np.array([prior_transform(_) for _ in live_u])
    live_logl = np.array([loglike(_) for _ in live_v])
    live_points = [live_u, live_v, live_logl, None]
    sampler = dynesty.NestedSampler(loglike,
                                    prior_transform,
                                    ndim,
                                    nlive=nlive,
                                    live_points=live_points,
                                    rstate=rstate)
    sampler.run_nested(print_progress=printing)
    dyutil.unravel_run(sampler.results)


def test_exc():
    # Test of exceptions that the exception is reraised
    ndim = 2
    rstate = get_rstate()
    with pytest.raises(MyException):
        sampler = dynesty.NestedSampler(loglike_exc,
                                        prior_transform,
                                        ndim,
                                        nlive=nlive,
                                        rstate=rstate)
        sampler.run_nested(print_progress=printing)


def test_neff():
    # test of neff functionality
    ndim = 2
    rstate = get_rstate()
    sampler = dynesty.NestedSampler(loglike,
                                    prior_transform,
                                    ndim,
                                    nlive=nlive,
                                    rstate=rstate)
    assert sampler.n_effective == 0
    sampler.run_nested(print_progress=printing)
    assert sampler.n_effective > 10

    sampler = dynesty.DynamicNestedSampler(loglike,
                                           prior_transform,
                                           ndim,
                                           nlive=nlive,
                                           rstate=rstate)
    assert sampler.n_effective == 0
    sampler.run_nested(dlogz_init=1, n_effective=1000, print_progress=printing)
    assert sampler.n_effective > 1000
    sampler = dynesty.DynamicNestedSampler(loglike,
                                           prior_transform,
                                           ndim,
                                           nlive=nlive,
                                           rstate=rstate)
    sampler.run_nested(dlogz_init=1,
                       n_effective=10000,
                       print_progress=printing)
    assert sampler.n_effective > 10000


def test_oldstop():
    # test of old stopping function functionality
    ndim = 2
    rstate = get_rstate()
    import dynesty.utils as dyutil
    stopfn = dyutil.old_stopping_function
    sampler = dynesty.DynamicNestedSampler(loglike,
                                           prior_transform,
                                           ndim,
                                           nlive=nlive,
                                           rstate=rstate)
    sampler.run_nested(dlogz_init=1,
                       n_effective=None,
                       stop_function=stopfn,
                       print_progress=printing)


def test_stop_nmc():
    # test stopping relying in n_mc
    ndim = 2
    rstate = get_rstate()
    sampler = dynesty.DynamicNestedSampler(loglike,
                                           prior_transform,
                                           ndim,
                                           nlive=nlive,
                                           rstate=rstate)
    sampler.run_nested(dlogz_init=1,
                       n_effective=None,
                       stop_kwargs=dict(n_mc=25),
                       print_progress=printing)


@pytest.mark.parametrize('dyn', [False, True])
def test_results(dyn):
    # test of various results interfaces functionality
    ndim = 2
    rstate = get_rstate()
    if dyn:
        sampler = dynesty.DynamicNestedSampler(loglike,
                                               prior_transform,
                                               ndim,
                                               nlive=nlive,
                                               rstate=rstate)
    else:
        sampler = dynesty.NestedSampler(loglike,
                                        prior_transform,
                                        ndim,
                                        nlive=nlive,
                                        rstate=rstate)
    sampler.run_nested(print_progress=printing)
    res = sampler.results
    for k in res.keys():
        pass
    for k, v in res.items():
        pass
    for k, v in res.asdict().items():
        pass
    print(res)
    print(str(res))
    print('logl' in res)
    # check attributes
    assert np.all(res.logz == res['logz'])
    assert np.all(res.logzerr == res['logzerr'])
    res1 = res.copy()
    del res1
    # check it's pickleable
    S = pickle.dumps(res)
    res = pickle.loads(S)


@pytest.mark.parametrize('ndim', [2, 10])
def test_deterministic(ndim):
    # test we are deterministic

    results = []
    for i in range(2):
        rstate = get_rstate()

        sampler = dynesty.DynamicNestedSampler(loglike,
                                               prior_transform,
                                               ndim,
                                               nlive=nlive,
                                               rstate=rstate)
        sampler.run_nested(print_progress=printing)
        res = sampler.results
        results.append(res)

    for k in results[0].keys():
        if k == 'blob':
            continue
        val0 = results[0][k]
        val1 = results[1][k]
        if (isinstance(val0, int) or isinstance(val0, float)
                or isinstance(val0, np.ndarray)):
            assert np.allclose(val0, val1)


def test_update_interval():
    # test that we cab set update_interval
    # ideally i'd need to see if it makes a difference...
    ndim = 2
    rstate = get_rstate()

    sampler = dynesty.NestedSampler(loglike,
                                    prior_transform,
                                    ndim,
                                    nlive=nlive,
                                    rstate=rstate,
                                    update_interval=10)
    sampler.run_nested(print_progress=printing)
    sampler = dynesty.NestedSampler(loglike,
                                    prior_transform,
                                    ndim,
                                    nlive=nlive,
                                    rstate=rstate,
                                    update_interval=0.5)
    sampler.run_nested(print_progress=printing)


def prior_transform_large_logl(u):
    scale = 10
    v = scale * (2 * u - 1)
    return v


def loglike_large_logl(v):
    logp = np.sum(-0.5 * v**2)
    if v[0] < 0:
        logp = -1e300
    return logp


def test_large_logl():
    # This is to test that the logzerr calculation is all right
    # if there are very large (negative) logl vaues
    # See bug #360
    ndim = 2
    rstate = get_rstate()
    sampler = dynesty.NestedSampler(loglike_large_logl,
                                    prior_transform_large_logl,
                                    ndim,
                                    sample='rslice',
                                    nlive=200,
                                    rstate=rstate)

    sampler.run_nested(print_progress=printing)
    res = sampler.results

    assert res.logzerr[-1] < 1


def test_norstate():
    # test it can work without rstate
    ndim = 2
    dynesty.NestedSampler(loglike, prior_transform, ndim, nlive=nlive)

    dynesty.DynamicNestedSampler(loglike, prior_transform, ndim, nlive=nlive)


def prior_transform_tuple(u):
    # test we can return tuples
    return u[0], u[1]


def loglike_transform_tuple(v):
    logp = np.sum(-0.5 * v**2)
    return logp


def test_transform_tuple():
    # This is to test that the logzerr calculation is all right
    # if there are very large (negative) logl vaues
    # See bug #360
    ndim = 2
    rstate = get_rstate()
    sampler = dynesty.NestedSampler(loglike_large_logl,
                                    prior_transform_large_logl,
                                    ndim,
                                    rstate=rstate)

    sampler.run_nested(print_progress=printing, maxiter=50)


class Like2:

    def __init__(self):
        self.ndim = 2
        self.C2 = np.identity(self.ndim)
        self.Cinv2 = linalg.inv(self.C2)
        self.lnorm2 = -0.5 * (np.log(2 * np.pi) * self.ndim +
                              np.log(linalg.det(self.C2)))

    def loglikelihood(self, x):
        """Multivariate normal log-likelihood."""
        return -0.5 * np.dot(x, np.dot(self.Cinv2, x)) + self.lnorm2

    # prior transform
    def prior_transform(self, u):
        return 10. * (2. * u - 1.)


def test_maxiter_batch():
    """
    This tests the situation when maxiter runs out before the batch has time to start
    See #392
    """
    maxiter0 = 10000

    L = Like2()
    nlive = 50
    for i in range(2):
        if i == 0:
            maxiter = maxiter0

        rstate = get_rstate()
        dsampler2 = dynesty.DynamicNestedSampler(L.loglikelihood,
                                                 L.prior_transform,
                                                 nlive=nlive,
                                                 ndim=L.ndim,
                                                 bound='single',
                                                 sample='unif',
                                                 rstate=rstate)

        dsampler2.run_nested(maxiter=maxiter, use_stop=False)
        dres2 = dsampler2.results
        if i == 0:
            # I am finding the the first iteration with the batch
            # [-inf, something]. Then I'm setting maxiter to be just above
            # that iteration
            b1 = np.where(~np.isfinite(dres2.batch_bounds[:, 0]))[0][1]
            maxiter = np.min(
                np.array(dsampler2.saved_run['it'])[
                    dsampler2.saved_run['batch'] == b1]) + nlive // 2


def test_quantile():
    rstate = get_rstate()
    with pytest.raises(Exception):
        dyutil.quantile(rstate.normal(size=10), -1)
    with pytest.raises(Exception):
        dyutil.quantile(rstate.normal(size=10), 1.1)
    dyutil.quantile(rstate.normal(size=10), 0.5)
    whts = np.ones(10)
    dyutil.quantile(rstate.normal(size=10), 0.5, weights=whts)
    with pytest.raises(Exception):
        dyutil.quantile(rstate.normal(size=10), 0.5, weights=np.ones(9))

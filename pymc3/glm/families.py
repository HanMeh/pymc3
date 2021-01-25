#   Copyright 2020 The PyMC Developers
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import numbers

from copy import copy

import aesara.tensor as aet
import numpy as np

from pymc3 import distributions as pm_dists
from pymc3.model import modelcontext

__all__ = ["Normal", "StudentT", "Binomial", "Poisson", "NegativeBinomial"]

# Define link functions

# Hack as assigning a function in the class definition automatically binds
# it as a method.


class Identity:
    def __call__(self, x):
        return x


identity = Identity()
logit = aet.nnet.sigmoid
inverse = aet.inv
exp = aet.exp


class Family:
    """Base class for Family of likelihood distribution and link functions."""

    priors = {}
    link = None

    def __init__(self, **kwargs):
        # Overwrite defaults
        for key, val in kwargs.items():
            if key == "priors":
                self.priors = copy(self.priors)
                self.priors.update(val)
            else:
                setattr(self, key, val)

    def _get_priors(self, model=None, name=""):
        """Return prior distributions of the likelihood.

        Returns
        -------
        dict: mapping name -> pymc3 distribution
        """
        if name:
            name = f"{name}_"
        model = modelcontext(model)
        priors = {}
        for key, val in self.priors.items():
            if isinstance(val, (numbers.Number, np.ndarray, np.generic)):
                priors[key] = val
            else:
                priors[key] = model.register_rv(val, f"{name}{key}")

        return priors

    def create_likelihood(self, name, y_est, y_data, model=None):
        """Create likelihood distribution of observed data.

        Parameters
        ----------
        y_est: aesara.tensor
            Estimate of dependent variable
        y_data: array
            Observed dependent variable
        """
        priors = self._get_priors(model=model, name=name)
        # Wrap y_est in link function
        priors[self.parent] = self.link(y_est)
        if name:
            name = f"{name}_"
        return self.likelihood(f"{name}y", observed=y_data, **priors)

    def __repr__(self):
        return """Family {klass}:
    Likelihood  : {likelihood}({parent})
    Priors      : {priors}
    Link function: {link}.""".format(
            klass=self.__class__,
            likelihood=self.likelihood.__name__,
            parent=self.parent,
            priors=self.priors,
            link=self.link,
        )


class StudentT(Family):
    link = identity
    likelihood = pm_dists.StudentT
    parent = "mu"
    # XXX: This won't be a healthy approach even after `HalfCauchy` is refactored
    priors = None  # {"lam": pm_dists.HalfCauchy.dist(beta=10, testval=1.0), "nu": 1}


class Normal(Family):
    link = identity
    likelihood = pm_dists.Normal
    parent = "mu"
    # XXX: This won't be a healthy approach even after `HalfCauchy` is refactored
    priors = None  # {"sd": pm_dists.HalfCauchy.dist(beta=10, testval=1.0)}


class Binomial(Family):
    link = logit
    likelihood = pm_dists.Binomial
    parent = "p"
    priors = {"n": 1}


class Poisson(Family):
    link = exp
    likelihood = pm_dists.Poisson
    parent = "mu"
    # XXX: This won't be a healthy approach even after `HalfCauchy` is refactored
    priors = None  # {"mu": pm_dists.HalfCauchy.dist(beta=10, testval=1.0)}


class NegativeBinomial(Family):
    link = exp
    likelihood = pm_dists.NegativeBinomial
    parent = "mu"
    # XXX: This won't be a healthy approach even after `HalfCauchy` is refactored
    priors = None  # {
    #     "mu": pm_dists.HalfCauchy.dist(beta=10, testval=1.0),
    #     "alpha": pm_dists.HalfCauchy.dist(beta=10, testval=1.0),
    # }

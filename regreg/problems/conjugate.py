from __future__ import print_function, division, absolute_import

from copy import copy

import numpy as np

from ..algorithms import FISTA
from ..smooth.quadratic import quadratic, smooth_atom
from .composite import composite
from .simple import simple_problem

from ..identity_quadratic import identity_quadratic

class conjugate(composite):

    def __init__(self, atom, quadratic=None, change_sign=False, **fit_args):
        
        # we copy the atom because we will modify its quadratic part
        self.atom = copy(atom)

        if quadratic is None:
            quadratic = identity_quadratic(0, 0, 0, 0)
        self.conjugate_quadratic = quadratic

        totalq = self.atom.quadratic + quadratic
        if totalq.coef in [0, None]:
            raise ValueError('quadratic coefficient must be non-zero')

        if isinstance(self.atom, smooth_atom):
            self.problem = simple_problem.smooth(self.atom)
        self.fit_args = fit_args

        #XXX we need a better way to pass around the Lipschitz constant
        # should go in the container class
#         if hasattr(self.atom, "lipschitz"):
#             self.fit_args['perform_backtrack'] = False
#         else:
#             self.fit_args['perform_backtrack'] = True

        self._have_solved_once = False
        self.shape = atom.shape

        # for various purposes,
        # we often want to evalute the conjugate of -x 
        # instead of x

        # change_sign saves composition with an affine transform

        self.change_sign = change_sign

    def smooth_objective(self, x, mode='both', check_feasibility=False):
        """
        Evaluate the conjugate function and/or its gradient

        if mode == 'both', return both function value and gradient
        if mode == 'grad', return only the gradient
        if mode == 'func', return only the function value
        """

        if self.change_sign:
            v = -x
        else:
            v = x

        old_lin = self.conjugate_quadratic.linear_term
        if old_lin is not None:
            new_lin = old_lin - v
        else:
            new_lin = -v
        self.conjugate_quadratic.linear_term = new_lin
        if isinstance(self.atom, smooth_atom):
            minimizer = self.problem.solve(self.conjugate_quadratic, max_its=5000, **self.fit_args)
        else: # it better have a proximal method!
            minimizer = self.atom.proximal(self.conjugate_quadratic)
        self.conjugate_quadratic.linear_term = old_lin
    
        # retain a reference
        self.argmin = minimizer

        if mode == 'both':
            val = self.atom.objective(minimizer)
            if not self.change_sign:
                return -val - self.conjugate_quadratic.objective(minimizer, mode='func') + (v * minimizer).sum(), minimizer
            else:
                return -val - self.conjugate_quadratic.objective(minimizer, mode='func') + (v * minimizer).sum(), -minimizer
        elif mode == 'func':
            val = self.atom.objective(minimizer)
            if not self.change_sign:
                return -val - self.conjugate_quadratic.objective(minimizer, mode='func') + (v * minimizer).sum()
            else:
                return -val - self.conjugate_quadratic.objective(minimizer, mode='func') + (v * minimizer).sum()
        elif mode == 'grad':
            if not self.change_sign:
                return minimizer
            else:
                return -minimizer
        else:
            raise ValueError("mode incorrectly specified")



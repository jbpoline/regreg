import numpy as np
from ..affine import affine_transform

class multiscale(affine_transform):

    """
    An affine transform representing the
    multiscale changepoint transform.

    This transform centers the input
    and then computes the average over
    all intervals of a minimum size.
    """

    dtype = np.dtype([('start', np.int),
                      ('end', np.int)])

    def __init__(self, p, minsize=None, slices=[],
                 scaling=None):
        """
        Parameters
        ----------

        p : int
            Length of signal.

        minsize : int
            Smallest interval to consider.
            Defaults to p**(1/3.)

        slices : []
            A list of intervals to use in the transform.
            Will be coerced to have dtype([('start', np.int), ('end', np.int)])

        scaling : np.float((slices.shape))
            An optional scaling to apply after computing
            mean over each interval.

        """
        self.p = p
        self.minsize = minsize or int(np.around(p**(1/3.)))
        self.slices = np.asarray(slices, self.dtype)
        self.scaling = scaling
        if self.slices.shape in [(), (0,)]:
            self._all = True # if computing all differences of a certain size things can be sped up
            S = np.indices((p,p)).reshape((2,-1))
            self._mask = (S[1]-S[0] >= self.minsize)
            slices = S[:,self._mask].T
            self.slices = np.empty(slices.shape[0], self.dtype)
            self.slices['start'] = slices[:,0]
            self.slices['end'] = slices[:,1]
        else:
            self._all = False
        self.sizes = self.slices['end'] - self.slices['start'] * 1.
        self.input_shape = (p,)
        self.output_shape = (len(self.slices),)

    def update_slices(self, slices, scaling=None):
        """

        Change the intervals computed by the multiscale
        transform.

        Parameters
        ----------

        slices : []
            List of (i,j) intervals to compute.
            Will be converted to have dtype([('start', np.int), ('end', np.int)])

        """
        slices = np.asarray(slices)
        if slices.dtype != self.dtype:
            self.slices = np.empty(slices.shape[0], self.dtype)
            self.slices['start'] = slices[:,0]
            self.slices['end'] = slices[:,1]
            self._all = False
        else:
            self.slices = slices
        self.sizes = self.slices['end'] - self.slices['start'] * 1.
        self.output_shape = (len(self.slices),)
        self.scaling = scaling

    def linear_map(self, x):
        """
        Given a p-vector `x` compute the average of
        `x - x.mean()` over each interval
        of size greater than `self.minsize`.

        Parameters
        ----------

        x : np.float(self.input_shape)

        Returns
        -------

        v : np.float(self.output_shape)

        """
        x_centered = x - x.mean()
        output = np.zeros(self.output_shape)
        cumsum = np.cumsum(x_centered)
        if not self._all:
            for k, ij in enumerate(self.slices):
                i, j = ij
                if i >= 1:
                    output[k] = cumsum[j-1] - cumsum[i-1] 
                else:
                    output[k] = cumsum[j-1]
                output[k] /= j - i
        else:
            _cumsum = np.hstack([np.zeros(1), cumsum])
            D = np.subtract.outer(_cumsum, _cumsum)[:-1,:-1].reshape(-1)[self._mask]
            output = -D / self.sizes
        if self.scaling is not None:
            output *= self.scaling
        return output

    def affine_map(self, x):
        return self.linear_map(x)

    def adjoint_map(self, v):
        """
        Parameters
        ----------

        v : np.float(self.output_shape)

        Returns
        -------

        v : np.float(self.input_shape)
        """

        v_scaled = v / self.sizes
        if self.scaling is not None:
            v_scaled *= self.scaling
        if not self._all:
            output = np.zeros(self.input_shape)
            non0 = np.nonzero(v_scaled)[0]
            if non0.shape != ():
                for k in non0:
                    i, j = self.slices[k]
                    output[i:j] += v_scaled[k]
        else:
            _output1 = np.zeros((self.input_shape[0], self.input_shape[0])).reshape(-1)
            _output1[self._mask] = v_scaled
            _output1.shape = (self.input_shape[0], self.input_shape[0])
            _output2 = _output1.sum(0) - _output1.sum(1)
            output = -np.cumsum(_output2)
        return output - output.mean()
        



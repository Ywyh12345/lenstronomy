
from lenstronomy.ImSim.Numerics.pixel_convolution import SubgridNumbaConvolution, NumbaConvolution
from lenstronomy.ImSim.Numerics.convolution import PixelKernelConvolution
from lenstronomy.Util import kernel_util
from lenstronomy.Util import image_util
from lenstronomy.Util import util


class AdaptiveNumerics(object):
    """
    this class manages and computes a surface brightness convolved image in an adaptive approach.
    The strategie applied are:
    1.1 surface brightness computation only where significant flux is expected
    1.2 super sampled surface brightness only in regimes of high spacial variability in the surface brightness and at
    high contrast
    2.1 convolution only applied where flux is present (avoid convolving a lot of zeros)
    2.2 simplified Multi-Gaussian convolution in regimes of low contrast
    2.3 (super-) sampled PSF convolution only at high contrast of highly variable sources


    the class performs the convolution with two different input arrays, one with low resolution and one on a subpart with high resolution

    """
    def __init__(self):
        pass

    def convolve2d(self, image_hig_res, image_low_res):
        """

        :param image_hig_res: super-sampled surface brightness
        :param image_low_res: regular sampled surface brightness
        :return: convolved image on regular grid
        """
        # add supersampled region to lower resolution on
        # convolve low res grid
        # make complete super-sampled grid (adding zeros)
        # convolve differences with numba on subpart (even subpart of the high resolution sampling)
        # combine convolutions (1 + 2 -3)


class AdaptiveConvolution(object):
    """
    This class performs convolutions of a subset of pixels at higher supersampled resolution
    Goal: speed up relative to higher resolution FFT when only considereing a (small) subset of pixels to be convolved
    on the higher resolution grid.

    strategy:
    1. lower resolution convolution over full image with FFT
    2. subset of pixels with higher resolution Numba convolution (with smaller kernel)
    3. the same subset of pixels with low resolution Numba convolution (with same kernel as step 2)
    adaptive solution is 1 + 2 -3

    """
    def __init__(self, kernel_super, supersampling_factor, conv_supersample_pixels, supersampling_size=None, compute_pixels=None, nopython=True, cache=True,
                 parallel=False):
        """

        :param kernel_super: convolution kernel in units of super sampled pixels provided, odd length per axis
        :param supersampling_factor: factor of supersampling relative to pixel grid
        :param conv_supersample_pixels: bool array same size as data, pixels to be convolved and their light to be blurred
        :param supersampling_size: number of pixels (in units of the image pixels) that are convolved with the
        supersampled kernel
        :param compute_pixels: bool array of size of image, these pixels (if True) will get blurred light from other pixels
        :param nopython: bool, numba jit setting to use python or compiled.
        :param cache: bool, numba jit setting to use cache
        :param parallel: bool, numba jit setting to use parallel mode
        """
        #kernel_pixel = kernel_util.kernel_average_pixel(kernel_super, supersampling_factor)
        n_high = len(kernel_super)
        numPix = int(n_high / supersampling_factor)
        if supersampling_factor % 2 == 0:
            kernel = kernel_util.averaging_even_kernel(kernel_super, supersampling_factor)
        else:
            kernel = util.averaging(kernel_super, numGrid=n_high,
                                                       numPix=numPix)
        kernel *= supersampling_factor**2
        self._low_res_conv = PixelKernelConvolution(kernel, convolution_type='fft')
        if supersampling_size is None:
            supersampling_size = len(kernel)

        kernel_cut = image_util.cut_edges(kernel, supersampling_size)
        kernel_super_cut = image_util.cut_edges(kernel_super, supersampling_size*supersampling_factor)
        self._low_res_partial = NumbaConvolution(kernel_cut, conv_supersample_pixels, compute_pixels=compute_pixels,
                                                 nopython=nopython, cache=cache, parallel=parallel, memory_raise=True)
        self._hig_res_partial = SubgridNumbaConvolution(kernel_super_cut, supersampling_factor, conv_supersample_pixels,
                                                        compute_pixels=compute_pixels, nopython=nopython, cache=cache,
                                                        parallel=parallel)#, kernel_size=len(kernel_cut))
        self._supersampling_factor = supersampling_factor

    def convolve2d(self, image_high_res):
        """

        :param image_high_res: supersampled image/model to be convolved on a regular pixel grid
        :return: convolved and re-sized image
        """
        image_low_res = image_util.re_size(image_high_res, factor=self._supersampling_factor)
        image_low_res_conv = self._low_res_conv.convolution2d(image_low_res)# * self._supersampling_factor**2 * self._supersampling_factor**2
        image_low_res_partial_conv = self._low_res_partial.convolve2d(image_low_res)# * self._supersampling_factor**2
        image_high_res_partial_conv = self._hig_res_partial.convolve2d(image_high_res)
        return image_low_res_conv + image_high_res_partial_conv - image_low_res_partial_conv
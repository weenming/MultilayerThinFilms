import numpy as np
import cmath
from numba import cuda
from mat_lib import mul # multiply
from mat_lib import tps # transpose



def get_spectrum_simple(spectrum, wls, d, n_layers, n_sub, n_inc, inc_ang):
    """
    This function calculates the reflectance and transmittance spectrum of a 
    non-polarized light (50% p-polarized and 50% s-polarized).

    Arguments:
        spectrum (1d np.array):
            pre-allocated memory space for returning spectrum 
        wls (1d np.array): 
            wavelengths of the target spectrum
        d (1d np.array):
            multi-layer thicknesses after last iteration
        n_layers (2d np.array): 
            size: wls.shape[0] \cross d.shape[0]. refractive indices of 
            each *layer*
        n_sub (1d np.array):
            refractive indices of the substrate
        n_inc (1d np.array):
            refractive indices of the incident material
        inc_ang (float):
            incident angle in degree

    Returns:
        size: 2 \cross wls.shape[0] spectrum 
        (Reflectance spectrum + Transmittance spectrum).
    """
    # layer number of thin film, substrate not included
    layer_number = d.shape[0]
    # convert incident angle in degree to rad
    inc_ang_rad = inc_ang / 180 * np.pi
    # traverse all wl, save R and T to the 2N*1 np.array spectrum. [R, T]
    wls_size = wls.shape[0]
    spectrum = np.empty(wls_size)

    # TODO: move the copy of wls, n arr to outer loop 
    # (caller of spec, for example LM optimizer) 
    # Maybe allowing it to pass in additional device arr would be a good idea

    # copy wls, d, n_layers, n_sub, n_inc, inc_ang to GPU
    wls_device = cuda.to_device(wls)
    d_device = cuda.to_device(d)
    # n = n_layers[tid, layer_index], but
    n_A_device = cuda.to_device(n_layers[:, 0]) 
    # may have only 1 layer. 
    if layer_number == 1:
        n_B_device = cuda.to_device(np.empty(wls_size))
    else:
        n_B_device = cuda.to_device(n_layers[:, 1])
     
    n_B_device = cuda.to_device(n_layers[:, 1])
    n_sub_device = cuda.to_device(n_sub)
    n_inc_device = cuda.to_device(n_inc)
    # primitive transfer is not costly so I leave out inc_ang, wls_size and 
    # layer_number
    spectrum_device = cuda.device_array(wls_size) # only R spec
    # invoke kernel
    block_size = 32 # threads per block
    grid_size = (wls_size + block_size - 1) // block_size # blocks per grid
    forward_propagation_simple[grid_size, block_size](
        spectrum_device,
        wls_device,
        d_device, 
        n_A_device,
        n_B_device,
        n_sub_device,
        n_inc_device,
        inc_ang_rad,
        wls_size,
        layer_number
    )
    # copy to pre-allocated space
    return spectrum_device.copy_to_host(spectrum)



@cuda.jit
def forward_propagation_simple(spectrum, wls, d, n_A, n_B, n_sub, n_inc, 
                               inc_ang, wl_size, layer_number):
    """
    n = n_layers[tid, layer_index]
    """
    thread_id = cuda.grid(1)
    # check this thread is valid
    if thread_id > wl_size:
        return
    # each thread calculates one wl    
    wl = wls[thread_id]

    # inc_ang is already in rad
    
    # incident angle in each layer. Snell's law: n_a sin(phi_a) = n_b sin(phi_b)
    cos_A = cmath.sqrt(1 - ((n_A / n_inc) * cmath.sin(inc_ang)) ** 2)
    cos_B = cmath.sqrt(1 - ((n_B / n_inc) * cmath.sin(inc_ang)) ** 2)
    cos_inc = cmath.cos(inc_ang)
    cos_sub = cmath.sqrt(1 - ((n_sub / n_inc) * cmath.sin(inc_ang)) ** 2)
    
    # choose cos from arr of size 2
    cos_arr = cuda.device_array(2, dtype="complex128")
    cos_arr[0] = cos_A
    cos_arr[1] = cos_B

    n_arr = cuda.device_array(2, dtype="complex128")
    n_arr[0] = n_A
    n_arr[1] = n_B      

    # Allocate space for M 
    Ms = cuda.device_array((2, 2), dtype="complex128")    
    Mp = cuda.device_array((2, 2), dtype="complex128")

    # Allocate space for W. Fill with first term D_{0}^{-1}
    # TODO: add the influence of n of incident material (when not air)
    Ws = cuda.device_array((2, 2), dtype="complex128")
    Ws[0, 0] = 0.5
    Ws[0, 1] = 0.5 / cmath.cos(inc_ang)
    Ws[1, 0] = 0.5
    Ws[1, 1] = -0.5 / cmath.cos(inc_ang)
    
    Wp = cuda.device_array((2, 2), dtype="complex128")
    Wp[0, 0] = 0.5
    Wp[0, 1] = 0.5 / cos_inc
    Ws[1, 0] = 0.5
    Ws[1, 1] = -0.5 / cos_inc

    for i in range(layer_number):
        cosi = cos_arr[i % 2]
        ni = n_arr[i % 2]
        phi = 2 * cmath.pi * 1j * cosi * ni * d[i] / wl

        coshi = cmath.cosh(phi)
        sinhi = cmath.sinh(phi)

        Ms[0, 0] = coshi
        Ms[0, 1] = sinhi / cosi / ni
        Ms[1, 0] = cosi * ni * sinhi
        Ms[1, 1] = coshi

        Mp[0, 0] = coshi
        Mp[0, 1] = sinhi * ni / cosi
        Mp[1, 0] = cosi / ni * sinhi
        Mp[1, 1] = coshi

        Ws = mul(Ws, Ms)
        Wp = mul(Wp, Mp)

    # construct the last term D_{n+1} 
    # technically this is not M which is D^{-1}PD but merely D 
    Ms[0, 0] = 1.
    Ms[0, 1] = 1.
    Ms[1, 0] = n_sub * cos_sub
    Ms[1, 1] = n_sub * cos_sub

    Mp[0, 0] = n_sub
    Mp[0, 1] = n_sub
    Mp[1, 0] = cos_sub
    Mp[1, 1] = cos_sub

    Ws = mul(Ws, Ms)
    Wp = mul(Wp, Mp)

    # retrieve R and T (calculate the factor before energy flux)
    # Note that spectrum is array on device
    rs = Ws[1, 0] / Ws[0, 0]
    rp = Wp[1, 0] / Wp[0, 0]
    R = (rs * rs.conjugate() + rp * rp.conjugate()) / 2
    spectrum[thread_id, 0] = R.real

    # T should be R - 1
    ts = 1 / Ws[0, 0]
    tp = 1 / Wp[0, 0]
    T = cos_sub / cos_inc * n_sub * (
        ts * ts.conjugate() + tp * tp.conjugate()) / 2
    spectrum[thread_id + wls.shape[0], 0] = T.real

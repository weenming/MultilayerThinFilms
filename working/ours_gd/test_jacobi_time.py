import unittest
import numpy as np
import sys
sys.path.append("./designer/script/")
sys.path.append("./designer/")
sys.path.append("./")
import os
import time
import film as film
import spectrum
import utils.get_n as get_n
import tmm.get_jacobi as get_jacobi
import tmm.tmm_cpu.get_jacobi as get_jacobi_cpu
import timeit
from optimizer.grad_helper import stack_J, stack_init_params
import matplotlib.pyplot as plt
import pickle


def jacobi_GPU(layer_number):
    np.random.seed(1)
    d_expected = np.random.random(layer_number) * 100

    substrate = A = "SiO2"
    B = "TiO2"
    f = film.TwoMaterialFilm(A, B, substrate, d_expected)
    # must set spec before calculating spec
    inc_ang = 60.  # incident angle in degree
    wls = np.linspace(500, 1000, 128000)
    f.add_spec_param(inc_ang, wls)

    jacobi = np.empty((wls.shape[0] * 2, layer_number))
    get_jacobi.get_jacobi_simple(jacobi, wls, f.get_d(),
                                 f.spectra[0].film.calculate_n_array(wls), f.spectra[0].n_sub, f.spectra[0].n_inc, inc_ang, jacobi.shape[1])


def jacobi_CPU(layer_number):
    assert layer_number % 2 == 0
    np.random.seed(1)
    d_expected = np.random.random(layer_number) * 100

    substrate = A = "SiO2"
    B = "TiO2"
    f = film.TwoMaterialFilm(A, B, substrate, d_expected)
    # must set spec before calculating spec
    inc_ang = 60.  # incident angle in degree
    wls = np.linspace(500, 1000, 500)
    f.add_spec_param(inc_ang, wls)

    materials = np.array([A, B] * (layer_number // 2))
    get_jacobi_cpu.get_jacobi(wls, f.get_d(), materials, theta0=inc_ang)


def dif_n(layer_number):
    N = 1
    t_gpu = timeit.timeit(
        f"jacobi_GPU({layer_number})", number=N, setup="from __main__ import jacobi_GPU")
    print(f"GPU, spectrum 500 wls: {t_gpu / N}")

    t_cpu = timeit.timeit(
        f"jacobi_CPU({layer_number})", number=N, setup="from __main__ import jacobi_CPU")
    print(f"CPU, spectrum 500 wls: {t_cpu / N}")

    return t_gpu / N, t_cpu / N


def dif_n_GPU(layer_number):
    N = 1
    t_gpu = timeit.timeit(
        f"jacobi_GPU({layer_number})", number=N, setup="from __main__ import jacobi_GPU")
    print(f"GPU, spectrum 500 wls: {t_gpu / N}")

    return t_gpu / N


def plot_time():
    # compile first
    dif_n(10)

    # start testing at different layer numbers
    # NOTE: max layer number is set in gets.get_jacobi
    Ns = np.array(range(10, 200, 20))
    Ts_GPU = []
    Ts_CPU = []
    for i in Ns:
        g, c = dif_n(i)
        Ts_CPU.append(c)
        Ts_GPU.append(g)

    k_cpu, b_cpu = np.polyfit(Ns, Ts_CPU, 1)
    k_gpu, b_gpu = np.polyfit(Ns, Ts_GPU, 1)
    N_e = np.linspace(0, Ns[-1], 1000)

    fig, ax = plt.subplots(1, 1)
    ax.scatter(Ns, Ts_CPU, label='CPU', marker='x')
    ax.plot(N_e, k_cpu * N_e + b_cpu, label='CPU fit')

    ax.scatter(Ns, Ts_GPU, label='GPU', marker='x')
    ax.plot(N_e, k_gpu * N_e + b_gpu, label='GPU fit')

    ax.legend()
    ax.set_xlabel("layer number")
    ax.set_ylabel("time / s")
    # ax.set_yscale('log')
    ax.set_xlim(0, Ns[-1])
    # plt.show()

    with open(os.path.dirname(__file__) + '/./../../../../working/review/computation/result', 'wb') as f:
        pickle.dump(
            {'jacobi': {
                'cpu': {
                    'layer_number': Ns,
                    'time': Ts_CPU
                }, 
                'gpu': {
                    'layer_number': Ns,
                    'time': Ts_GPU
                }
            }}, f)


def plot_time_GPU():
    # compile first
    dif_n(10)

    # start testing at different layer numbers
    # NOTE: max layer number is set in gets.get_jacobi
    Ns = np.array(range(10, 20, 1))
    print(Ns)
    Ts_GPU = []
    for i in Ns:
        for _ in range(100):
            g = dif_n_GPU(i)
            Ts_GPU.append(g)

    k_gpu, b_gpu = np.polyfit(Ns, Ts_GPU, 1)
    N_e = np.linspace(0, Ns[-1], 1000)

    fig, ax = plt.subplots(1, 1)
    ax.scatter(Ns, Ts_GPU, label='GPU', marker='x')
    ax.plot(N_e, k_gpu * N_e + b_gpu, label='GPU fit')
    ax.legend()
    ax.set_xlabel("layer number")
    ax.set_ylabel("time / s")
    # ax.set_yscale('log')
    ax.set_xlim(0, Ns[-1])
    ax.set_ylim(0, k_gpu * N_e[-1] + b_gpu)

    plt.show()


if __name__ == "__main__":
    plot_time_GPU()

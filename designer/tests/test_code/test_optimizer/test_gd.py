import sys
sys.path.append('./designer/script/')

import unittest
import numpy as np
import matplotlib.pyplot as plt

from film import FilmSimple
from spectrum import Spectrum
from optimizer.LM_gradient_descent import LM_optimize_d_simple
from optimizer.adam import adam_optimize
from design import DesignForSpecSimple


class TestGD(unittest.TestCase):
    def test_adam(self):
        
        wls = np.linspace(400, 1000, 1000, dtype='float')
        target_spec_R = np.ones(wls.shape[0], dtype='float')
        target_spec = Spectrum(0., wls, target_spec_R)

        d_init = np.random.random(500) * 50. # integer times of MAX
        init_film = FilmSimple('SiO2', 'TiO2', 'SiO2', d_init)
        design = DesignForSpecSimple(target_spec, init_film)
        adam_optimize(design.film, design.
        target_specs, max_steps=50, alpha=0.1, show=True)
        
        d_init = np.random.random(523) * 50. # not integer times of MAX
        init_film = FilmSimple('SiO2', 'TiO2', 'SiO2', d_init)
        design = DesignForSpecSimple(target_spec, init_film)
        adam_optimize(design.film, design.target_specs, max_steps=50, alpha=0.1, show=True)

    def test_LM(self):
        
        wls = np.linspace(400, 1000, 1000, dtype='float')
        target_spec_R = np.ones(wls.shape[0], dtype='float')
        target_spec = Spectrum(0., wls, target_spec_R)

        d_init = np.random.random(500) * 50. # integer times of MAX
        init_film = FilmSimple('SiO2', 'TiO2', 'SiO2', d_init)
        design = DesignForSpecSimple(target_spec, init_film)
        LM_optimize_d_simple(design.film, design.target_specs, 1e-200, 1000, show=True)
        
        d_init = np.random.random(523) * 50. # not integer times of MAX
        init_film = FilmSimple('SiO2', 'TiO2', 'SiO2', d_init)
        design = DesignForSpecSimple(target_spec, init_film)
        LM_optimize_d_simple(design.film, design.target_specs, 1e-200, 1000, show=True)


def make_design():
    wls = np.linspace(400, 1000, 1000, dtype='float')
    target_spec_R = np.ones(wls.shape[0], dtype='float')
    target_spec = Spectrum(0., wls, target_spec_R)

    d_init = np.random.random(520) * 100.
    init_film = FilmSimple('SiO2', 'TiO2', 'SiO2', d_init)

    design = DesignForSpecSimple(target_spec, init_film)
    return design

def LM_descent_test(design: DesignForSpecSimple):
    LM_optimize_d_simple(design.film, design.target_specs, 1e-200, 1000, show=True)

def Adam_descent_test(design: DesignForSpecSimple):
    adam_optimize(design.film, design.target_specs, max_steps=5000, alpha=0.01, show=True)
    '''
    As layer number increases, step size needs to decrease
    '''


if __name__ == '__main__':
    for seed in [0, 100, 233, 42, 555] + list(np.arange(20)):
        print(f'seed: {seed}')
        np.random.seed(seed)
        design = make_design()
        Adam_descent_test(design)
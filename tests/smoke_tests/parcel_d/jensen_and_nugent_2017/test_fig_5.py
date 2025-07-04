# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

from pathlib import Path

import numpy as np
import pytest
from scipy import signal

from open_atmos_jupyter_utils import notebook_vars
from PySDM_examples import Jensen_and_Nugent_2017
from PySDM.physics.constants import PER_CENT
from PySDM.physics import si
from .test_fig_4_and_7_and_tab_4_bottom_rows import (
    find_cloud_base_index,
    find_max_alt_index,
)

PLOT = False
N_SD = Jensen_and_Nugent_2017.simulation.N_SD_NON_GCCN + np.count_nonzero(
    Jensen_and_Nugent_2017.table_3.NA
)


@pytest.fixture(scope="session", name="variables")
def variables_fixture():
    return notebook_vars(
        file=Path(Jensen_and_Nugent_2017.__file__).parent / "Fig_5.ipynb", plot=PLOT
    )


class TestFig5:
    @staticmethod
    def test_height_range(variables):
        """note: in the plot the y-axis has cloud-base height subtracted, here not"""
        z_minus_z0 = (
            np.asarray(variables["output"]["products"]["z"]) - variables["settings"].z0
        )
        epsilon = 1 * si.m
        assert 0 <= min(z_minus_z0) < max(z_minus_z0) < 600 * si.m + epsilon

    @staticmethod
    def test_cloud_base_height(variables):
        cloud_base_index = find_cloud_base_index(variables["output"]["products"])

        z0 = variables["settings"].z0
        assert (
            290 * si.m
            < variables["output"]["products"]["z"][cloud_base_index] - z0
            < 300 * si.m
        )

    @staticmethod
    @pytest.mark.xfail(strict=True, reason="TODO #1266")
    def test_saturation_maximum(variables):
        saturation = np.asarray(variables["output"]["products"]["S_max"])
        assert signal.argrelextrema(saturation, np.greater)[0].shape[0] == 1
        assert 1.2 * PER_CENT < np.nanmax(saturation - 1) < 1.4 * PER_CENT

    @staticmethod
    @pytest.mark.parametrize("drop_id", range(int(0.8 * N_SD), N_SD))
    def test_radii(variables, drop_id):
        """checks that the largest aerosol activate and still grow upon descent"""
        # arrange
        cb_idx = find_cloud_base_index(variables["output"]["products"])
        ma_idx = find_max_alt_index(variables["output"]["products"])

        radii = variables["output"]["attributes"]["radius"][drop_id]
        r1 = radii[0]
        r2 = radii[cb_idx]
        r3 = radii[ma_idx]
        r4 = radii[-1]

        assert r1 < r2 < r3
        assert r3 < r4

    @staticmethod
    def test_maximal_size_of_largest_droplet(variables):
        np.testing.assert_approx_equal(
            max(variables["output"]["attributes"]["radius"][-1]),
            56 * si.um,
            significant=2,
        )

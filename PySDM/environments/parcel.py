"""
Zero-dimensional adiabatic parcel framework
"""

from typing import List, Optional, Union

import numpy as np

from PySDM.environments.impl.moist import Moist
from PySDM.impl.mesh import Mesh
from PySDM.initialisation.hygroscopic_equilibrium import (
    default_rtol,
    equilibrate_wet_radii,
)
from PySDM.environments.impl import register_environment


@register_environment()
class Parcel(Moist):  # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        *,
        dt,
        mass_of_dry_air: float,
        p0: float,
        initial_water_vapour_mixing_ratio: float,
        T0: float,
        w: Union[float, callable],
        z0: float = 0,
        mixed_phase=False,
        variables: Optional[List[str]] = None,
    ):
        variables = (variables or []) + ["rhod", "z"]
        super().__init__(dt, Mesh.mesh_0d(), variables, mixed_phase=mixed_phase)

        self.p0 = p0
        self.initial_water_vapour_mixing_ratio = initial_water_vapour_mixing_ratio
        self.T0 = T0
        self.z0 = z0
        self.mass_of_dry_air = mass_of_dry_air
        self.w = w if callable(w) else lambda _: w
        self.delta_liquid_water_mixing_ratio = np.nan

    @property
    def dv(self):
        rhod_mean = (self.get_predicted("rhod")[0] + self["rhod"][0]) / 2
        return self.particulator.formulae.trivia.volume_of_density_mass(
            rhod_mean, self.mass_of_dry_air
        )

    def register(self, builder):
        formulae = builder.particulator.formulae
        pd0 = formulae.trivia.p_d(self.p0, self.initial_water_vapour_mixing_ratio)
        rhod0 = formulae.state_variable_triplet.rhod_of_pd_T(pd0, self.T0)
        self.mesh.dv = formulae.trivia.volume_of_density_mass(
            rhod0, self.mass_of_dry_air
        )

        Moist.register(self, builder)

        self["water_vapour_mixing_ratio"][:] = self.initial_water_vapour_mixing_ratio
        self["thd"][:] = formulae.trivia.th_std(pd0, self.T0)
        self["rhod"][:] = rhod0
        self["z"][:] = self.z0

        self._tmp["water_vapour_mixing_ratio"][
            :
        ] = self.initial_water_vapour_mixing_ratio
        self.sync_parcel_vars()
        Moist.sync(self)
        self.notify()

    def init_attributes(
        self,
        *,
        n_in_dv: [float, np.ndarray],
        kappa: float,
        r_dry: [float, np.ndarray],
        rtol=default_rtol,
        include_dry_volume_in_attribute: bool = True,
    ):
        if not isinstance(n_in_dv, np.ndarray):
            r_dry = np.array([r_dry])
            n_in_dv = np.array([n_in_dv])

        attributes = {}
        dry_volume = self.particulator.formulae.trivia.volume(radius=r_dry)
        attributes["kappa times dry volume"] = dry_volume * kappa
        attributes["multiplicity"] = n_in_dv
        r_wet = equilibrate_wet_radii(
            r_dry=r_dry,
            environment=self,
            kappa_times_dry_volume=attributes["kappa times dry volume"],
            rtol=rtol,
        )
        attributes["volume"] = self.particulator.formulae.trivia.volume(radius=r_wet)
        if include_dry_volume_in_attribute:
            attributes["dry volume"] = dry_volume
        return attributes

    def advance_parcel_vars(self):
        """compute new values of displacement, dry-air density and volume,
        and write them to self._tmp and self.mesh.dv"""
        dt = self.particulator.dt
        formulae = self.particulator.formulae
        T = self["T"][0]
        p = self["p"][0]

        dz_dt = self.w((self.particulator.n_steps + 1 / 2) * dt)  # "mid-point"
        water_vapour_mixing_ratio = (
            self["water_vapour_mixing_ratio"][0]
            - self.delta_liquid_water_mixing_ratio / 2
        )

        # derivative evaluated at p_old, T_old, mixrat_mid, w_mid
        drho_dz = formulae.hydrostatics.drho_dz(
            p=p,
            T=T,
            water_vapour_mixing_ratio=water_vapour_mixing_ratio,
            lv=formulae.latent_heat_vapourisation.lv(T),
            d_liquid_water_mixing_ratio__dz=(
                self.delta_liquid_water_mixing_ratio / dz_dt / dt
            ),
        )
        drhod_dz = drho_dz  # TODO #407

        self.particulator.backend.explicit_euler(self._tmp["z"], dt, dz_dt)
        self.particulator.backend.explicit_euler(
            self._tmp["rhod"], dt, dz_dt * drhod_dz
        )

        self.mesh.dv = formulae.trivia.volume_of_density_mass(
            (self._tmp["rhod"][0] + self["rhod"][0]) / 2, self.mass_of_dry_air
        )

    def get_thd(self):
        return self["thd"]

    def get_water_vapour_mixing_ratio(self):
        return self["water_vapour_mixing_ratio"]

    def sync_parcel_vars(self):
        self.delta_liquid_water_mixing_ratio = (
            self._tmp["water_vapour_mixing_ratio"][0]
            - self["water_vapour_mixing_ratio"][0]
        )
        for var in self.variables:
            self._tmp[var][:] = self[var][:]

    def sync(self):
        self.sync_parcel_vars()
        self.advance_parcel_vars()
        super().sync()

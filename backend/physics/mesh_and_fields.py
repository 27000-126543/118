import numpy as np
from scipy.special import legendre, lpmv
from typing import Tuple, Optional, Dict, Any
import json
import os


class SphericalShellMesh:
    def __init__(
        self,
        outer_radius: float,
        inner_radius: float,
        n_radial: int = 32,
        n_theta: int = 64,
        n_phi: int = 128
    ):
        self.outer_radius = outer_radius
        self.inner_radius = inner_radius
        self.n_radial = n_radial
        self.n_theta = n_theta
        self.n_phi = n_phi

        self.r = None
        self.theta = None
        self.phi = None
        self.R, self.Theta, self.Phi = None, None, None
        self.dr = None
        self.dtheta = None
        self.dphi = None
        self.volume = None

    def generate(self) -> Dict[str, Any]:
        self.r = np.linspace(self.inner_radius, self.outer_radius, self.n_radial)
        self.theta = np.linspace(1e-10, np.pi - 1e-10, self.n_theta)
        self.phi = np.linspace(0, 2 * np.pi, self.n_phi, endpoint=False)

        self.R, self.Theta, self.Phi = np.meshgrid(
            self.r, self.theta, self.phi, indexing='ij'
        )

        self.dr = self.r[1] - self.r[0] if self.n_radial > 1 else 0
        self.dtheta = self.theta[1] - self.theta[0] if self.n_theta > 1 else 0
        self.dphi = self.phi[1] - self.phi[0] if self.n_phi > 1 else 0

        self.volume = self.R**2 * np.sin(self.Theta) * self.dr * self.dtheta * self.dphi

        return {
            'r': self.r.tolist(),
            'theta': self.theta.tolist(),
            'phi': self.phi.tolist(),
            'shape': (self.n_radial, self.n_theta, self.n_phi),
            'dr': self.dr,
            'dtheta': self.dtheta,
            'dphi': self.dphi,
            'total_volume': float(np.sum(self.volume))
        }

    def save(self, filepath: str):
        mesh_data = self.generate()
        with open(filepath, 'w') as f:
            json.dump(mesh_data, f)

    def spherical_to_cartesian(self, r, theta, phi):
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        return x, y, z


class FieldInitializer:
    def __init__(self, mesh: SphericalShellMesh):
        self.mesh = mesh
        self.R = mesh.R
        self.Theta = mesh.Theta
        self.Phi = mesh.Phi

    def initialize_magnetic_field(
        self,
        dipole_moment: float = 8.0e22,
        seed: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        np.random.seed(seed)

        mu0 = 4 * np.pi * 1e-7
        factor = mu0 * dipole_moment / (4 * np.pi * self.R**3)

        B_r = 2 * factor * np.cos(self.Theta)
        B_theta = factor * np.sin(self.Theta)
        B_phi = np.zeros_like(self.R)

        noise_level = 0.05
        B_r += noise_level * np.random.randn(*self.R.shape) * np.max(np.abs(B_r))
        B_theta += noise_level * np.random.randn(*self.R.shape) * np.max(np.abs(B_theta))
        B_phi += 0.02 * np.random.randn(*self.R.shape) * np.max(np.abs(B_r))

        r_inner_mask = self.R < 1.2 * self.mesh.inner_radius
        B_r[r_inner_mask] *= 0.1
        B_theta[r_inner_mask] *= 0.1
        B_phi[r_inner_mask] *= 0.1

        return B_r, B_theta, B_phi

    def initialize_temperature_field(
        self,
        cmb_heat_flux: float,
        icb_heat_flux: float,
        thermal_conductivity: float = 40.0
    ) -> np.ndarray:
        r_norm = (self.R - self.mesh.inner_radius) / (self.mesh.outer_radius - self.mesh.inner_radius)

        delta_T = 1000.0
        T_cmb = 3000.0
        T_icb = T_cmb + delta_T

        T = T_cmb + (T_icb - T_cmb) * (1 - r_norm**2)

        l_max = 4
        for l in range(2, l_max + 1, 2):
            for m in range(0, l + 1):
                amplitude = 50.0 / (l**2 + m**2 + 1)
                Y_lm = lpmv(m, l, np.cos(self.Theta)) * np.cos(m * self.Phi)
                T += amplitude * Y_lm * (1 - r_norm) * r_norm

        boundary_thickness = 0.05 * (self.mesh.outer_radius - self.mesh.inner_radius)
        inner_bl = self.R < self.mesh.inner_radius + boundary_thickness
        outer_bl = self.R > self.mesh.outer_radius - boundary_thickness
        T[inner_bl] = np.linspace(T_icb, T_icb - 200, np.sum(inner_bl)).reshape(T[inner_bl].shape)
        T[outer_bl] = np.linspace(T_cmb + 200, T_cmb, np.sum(outer_bl)).reshape(T[outer_bl].shape)

        return T

    def initialize_velocity_field(
        self,
        max_speed: float = 0.001,
        seed: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        np.random.seed(seed)

        r_norm = (self.R - self.mesh.inner_radius) / (self.mesh.outer_radius - self.mesh.inner_radius)

        envelope = r_norm * (1 - r_norm)

        v_r = max_speed * envelope * (
            np.sin(2 * self.Theta) * np.cos(self.Phi) +
            0.3 * np.sin(4 * self.Theta) * np.cos(2 * self.Phi)
        )
        v_theta = max_speed * envelope * (
            np.cos(self.Theta) * np.cos(self.Phi) * np.cos(2 * self.Theta) +
            0.2 * np.random.randn(*self.R.shape)
        )
        v_phi = max_speed * envelope * (
            np.sin(self.Theta) * np.sin(self.Phi) * 0.5 +
            0.1 * np.random.randn(*self.R.shape)
        )

        boundary_thickness = 0.03 * (self.mesh.outer_radius - self.mesh.inner_radius)
        v_r[self.R < self.mesh.inner_radius + boundary_thickness] = 0
        v_r[self.R > self.mesh.outer_radius - boundary_thickness] = 0
        v_theta[self.R < self.mesh.inner_radius + boundary_thickness] = 0
        v_theta[self.R > self.mesh.outer_radius - boundary_thickness] = 0
        v_phi[self.R < self.mesh.inner_radius + boundary_thickness] = 0
        v_phi[self.R > self.mesh.outer_radius - boundary_thickness] = 0

        return v_r, v_theta, v_phi


class DimensionlessNumbers:
    @staticmethod
    def calculate(
        core_radius: float,
        viscosity: float,
        thermal_expansion: float,
        density: float = 13000.0,
        gravity: float = 10.0,
        delta_T: float = 1000.0,
        thermal_diffusivity: float = 1e-5,
        magnetic_diffusivity: float = 2.0,
        rotation_rate: float = 7.29e-5
    ) -> Dict[str, float]:
        L = core_radius
        nu = viscosity / density
        kappa = thermal_diffusivity
        eta = magnetic_diffusivity
        Omega = rotation_rate

        Ra = (gravity * thermal_expansion * delta_T * L**3) / (nu * kappa)
        Pr = nu / kappa
        Pm = nu / eta
        Rm = (nu / eta) * Ra / Pr
        Ek = nu / (Omega * L**2)
        Ro = np.sqrt(Ek * Pr / Ra)
        Q = (Omega**2 * L**4) / (nu * eta)
        Di = (thermal_expansion * L * gravity) / (Omega**2 * L**2)

        U_typical = np.sqrt(gravity * thermal_expansion * delta_T * L)
        tau_viscous = L**2 / nu
        tau_thermal = L**2 / kappa
        tau_magnetic = L**2 / eta

        return {
            'rayleigh_number': float(Ra),
            'prandtl_number': float(Pr),
            'magnetic_prandtl_number': float(Pm),
            'magnetic_reynolds_number': float(Rm),
            'ekman_number': float(Ek),
            'rossby_number': float(Ro),
            'chandrasekhar_number': float(Q),
            'dissipation_number': float(Di),
            'typical_velocity': float(U_typical),
            'viscous_diffusion_time': float(tau_viscous),
            'thermal_diffusion_time': float(tau_thermal),
            'magnetic_diffusion_time': float(tau_magnetic),
            'density': density,
            'gravity': gravity,
            'delta_T': delta_T,
            'thermal_diffusivity': thermal_diffusivity,
            'magnetic_diffusivity': magnetic_diffusivity,
            'rotation_rate': rotation_rate
        }

    @staticmethod
    def calculate_relaxation_time(
        magnetic_reynolds: float,
        magnetic_diffusion_time: float
    ) -> float:
        if magnetic_reynolds > 1:
            return magnetic_diffusion_time / magnetic_reynolds
        return magnetic_diffusion_time

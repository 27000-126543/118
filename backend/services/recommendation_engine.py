import numpy as np
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pickle

from sqlalchemy.orm import Session

from backend.models import Simulation, Recommendation, SimulationStatus

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import r2_score, mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    RandomForestRegressor = None
    GradientBoostingRegressor = None
    StandardScaler = None
    train_test_split = None
    r2_score = None
    mean_squared_error = None


class PhysicalConstants:
    EARTH_AGE = 4.54e9
    INNER_CORE_FORMATION_AGE = 1.0e9
    CURRENT_DIPOLE_MOMENT = 8.0e22
    CURRENT_REVERSAL_FREQUENCY = 0.01
    CURRENT_VISCOSITY = 1e-2
    CURRENT_IC_GROWTH_RATE = 1e-12
    GRAVITY = 10.0
    DENSITY = 13000.0
    THERMAL_DIFFUSIVITY = 1e-5
    MAGNETIC_DIFFUSIVITY = 2.0
    THERMAL_EXPANSION = 1e-5
    CORE_RADIUS = 3.48e6
    CURRENT_INNER_CORE_RADIUS = 1.22e6
    ROTATION_RATE = 7.29e-5
    MU0 = 4 * np.pi * 1e-7


class RecommendationEngine:
    def __init__(self, db: Session, model_dir: str = './models'):
        self.db = db
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.sklearn_available = SKLEARN_AVAILABLE

        self.viscosity_model: Optional[Any] = None
        self.ic_growth_model: Optional[Any] = None
        self.scaler: Optional[Any] = None
        self.feature_names: List[str] = []

        self.model_path = os.path.join(model_dir, 'recommendation_models.pkl')
        self._load_models()

    def _load_models(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.viscosity_model = data['viscosity_model']
                    self.ic_growth_model = data['ic_growth_model']
                    self.scaler = data['scaler']
                    self.feature_names = data['feature_names']
            except Exception:
                pass

    def _save_models(self):
        data = {
            'viscosity_model': self.viscosity_model,
            'ic_growth_model': self.ic_growth_model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }
        with open(self.model_path, 'wb') as f:
            pickle.dump(data, f)

    def _engineer_features(self, sim: Simulation) -> Dict[str, float]:
        features = {}

        features['core_radius'] = float(getattr(sim, 'core_radius', PhysicalConstants.CORE_RADIUS) or PhysicalConstants.CORE_RADIUS)
        features['thermal_expansion'] = float(getattr(sim, 'thermal_expansion', PhysicalConstants.THERMAL_EXPANSION) or PhysicalConstants.THERMAL_EXPANSION)
        features['icb_heat_flux'] = float(getattr(sim, 'icb_heat_flux', 0.1) or 0.1)
        features['cmb_heat_flux'] = float(getattr(sim, 'cmb_heat_flux', 0.05) or 0.05)
        features['inner_core_radius'] = float(getattr(sim, 'inner_core_radius', PhysicalConstants.CURRENT_INNER_CORE_RADIUS) or PhysicalConstants.CURRENT_INNER_CORE_RADIUS)
        features['dipole_moment'] = float(getattr(sim, 'dipole_moment', PhysicalConstants.CURRENT_DIPOLE_MOMENT) or PhysicalConstants.CURRENT_DIPOLE_MOMENT)
        features['dipole_tilt'] = float(getattr(sim, 'dipole_tilt', 10.0) or 10.0)
        features['magnetic_energy'] = float(getattr(sim, 'total_magnetic_energy', 1e25) or 1e25)
        features['kinetic_energy'] = float(getattr(sim, 'total_kinetic_energy', 1e22) or 1e22)
        features['polarity_reversal_count'] = float(getattr(sim, 'polarity_reversal_count', 0) or 0)
        features['magnetic_energy_generation_efficiency'] = float(getattr(sim, 'magnetic_energy_generation_efficiency', 0.01) or 0.01)
        features['relaxation_time'] = float(getattr(sim, 'relaxation_time', 1e12) or 1e12)

        rayleigh = float(getattr(sim, 'rayleigh_number', None) or 0.0)
        prandtl = float(getattr(sim, 'prandtl_number', None) or 0.0)
        magnetic_reynolds = float(getattr(sim, 'magnetic_reynolds_number', None) or 0.0)
        ekman = float(getattr(sim, 'ekman_number', None) or 0.0)

        if rayleigh == 0 or prandtl == 0:
            viscosity = float(getattr(sim, 'viscosity', PhysicalConstants.CURRENT_VISCOSITY) or PhysicalConstants.CURRENT_VISCOSITY)
            L = features['core_radius']
            delta_T = 1000.0
            nu = viscosity / PhysicalConstants.DENSITY
            rayleigh = (PhysicalConstants.GRAVITY * features['thermal_expansion'] * delta_T * L**3) / (nu * PhysicalConstants.THERMAL_DIFFUSIVITY)
            prandtl = nu / PhysicalConstants.THERMAL_DIFFUSIVITY
            magnetic_reynolds = nu / PhysicalConstants.MAGNETIC_DIFFUSIVITY * rayleigh / prandtl
            ekman = nu / (PhysicalConstants.ROTATION_RATE * L**2)

        features['rayleigh_number'] = float(rayleigh)
        features['prandtl_number'] = float(prandtl)
        features['magnetic_reynolds_number'] = float(magnetic_reynolds)
        features['ekman_number'] = float(ekman)

        features['ra_pr_product'] = float(rayleigh * prandtl)
        features['ra_pr_ratio'] = float(rayleigh / max(prandtl, 1e-10))
        features['ra_sqrt'] = float(np.sqrt(max(rayleigh, 0.0)))
        features['pr_log'] = float(np.log10(max(prandtl, 1e-10)))

        current_iter = float(getattr(sim, 'current_iteration', 1) or 1)
        features['polarity_reversal_rate'] = float(features['polarity_reversal_count'] / max(current_iter, 1))
        features['reversal_rate_per_magnetic_time'] = float(
            features['polarity_reversal_rate'] * max(magnetic_reynolds, 1.0)
        )

        if features['kinetic_energy'] > 0:
            features['magnetic_to_kinetic_ratio'] = float(features['magnetic_energy'] / max(features['kinetic_energy'], 1e-10))
        else:
            features['magnetic_to_kinetic_ratio'] = 0.0

        if features['dipole_moment'] > 0:
            features['energy_per_dipole'] = float(features['magnetic_energy'] / max(features['dipole_moment'], 1e-10))
        else:
            features['energy_per_dipole'] = 0.0

        if features['polarity_reversal_count'] > 0:
            features['energy_per_reversal'] = float(features['magnetic_energy'] / max(features['polarity_reversal_count'], 1))
        else:
            features['energy_per_reversal'] = float(features['magnetic_energy'])

        if magnetic_reynolds > 0:
            features['dynamo_efficiency'] = float(features['magnetic_energy_generation_efficiency'] * np.sqrt(max(magnetic_reynolds, 0.0)))
        else:
            features['dynamo_efficiency'] = float(features['magnetic_energy_generation_efficiency'])

        inner_core_ratio = features['inner_core_radius'] / max(features['core_radius'], 1e-10)
        features['inner_core_volume_ratio'] = float(inner_core_ratio ** 3)
        features['outer_core_thickness'] = float(features['core_radius'] - features['inner_core_radius'])

        total_heat_flux = features['icb_heat_flux'] + features['cmb_heat_flux']
        if total_heat_flux > 0:
            features['heat_flux_partition'] = float(features['icb_heat_flux'] / max(total_heat_flux, 1e-10))
        else:
            features['heat_flux_partition'] = 0.5

        return features

    def _collect_training_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
        completed_sims = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.COMPLETED,
            Simulation.total_magnetic_energy.isnot(None),
            Simulation.dipole_moment.isnot(None)
        ).all()

        features = []
        target_viscosity = []
        target_ic_growth = []

        feature_names = [
            'core_radius', 'thermal_expansion', 'icb_heat_flux',
            'cmb_heat_flux', 'inner_core_radius',
            'dipole_moment', 'dipole_tilt', 'magnetic_energy',
            'kinetic_energy', 'polarity_reversal_count',
            'magnetic_energy_generation_efficiency', 'relaxation_time',
            'rayleigh_number', 'prandtl_number', 'magnetic_reynolds_number', 'ekman_number',
            'ra_pr_product', 'ra_pr_ratio', 'ra_sqrt', 'pr_log',
            'polarity_reversal_rate', 'reversal_rate_per_magnetic_time',
            'magnetic_to_kinetic_ratio', 'energy_per_dipole', 'energy_per_reversal',
            'dynamo_efficiency', 'inner_core_volume_ratio', 'outer_core_thickness',
            'heat_flux_partition'
        ]

        for sim in completed_sims:
            if sim.viscosity is None or sim.inner_core_radius is None:
                continue

            engineered = self._engineer_features(sim)

            row = []
            for feat in feature_names:
                val = engineered.get(feat, 0.0)
                row.append(float(val))

            features.append(row)
            target_viscosity.append(float(sim.viscosity))
            target_ic_growth.append(float(sim.inner_core_radius))

        self.feature_names = feature_names
        return (
            np.array(features),
            np.array(target_viscosity),
            np.array(target_ic_growth),
            feature_names
        )

    def train(self, test_size: float = 0.2) -> Dict[str, Any]:
        X, y_visc, y_ic, feature_names = self._collect_training_data()

        if len(X) < 10:
            return {
                'success': False,
                'message': f'Insufficient training data: {len(X)} samples (minimum 10 required)',
                'sklearn_available': self.sklearn_available,
                'available_samples': len(X)
            }

        if not self.sklearn_available:
            return {
                'success': False,
                'message': 'scikit-learn not available. Install with: pip install scikit-learn',
                'sklearn_available': False,
                'fallback': 'Using heuristic recommendation engine'
            }

        try:
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)

            X_train, X_test, y_visc_train, y_visc_test = train_test_split(
                X_scaled, y_visc, test_size=test_size, random_state=42
            )
            _, _, y_ic_train, y_ic_test = train_test_split(
                X_scaled, y_ic, test_size=test_size, random_state=42
            )

            self.viscosity_model = RandomForestRegressor(
                n_estimators=100, max_depth=15, random_state=42, n_jobs=-1
            )
            self.viscosity_model.fit(X_train, y_visc_train)

            self.ic_growth_model = GradientBoostingRegressor(
                n_estimators=100, max_depth=8, learning_rate=0.1, random_state=42
            )
            self.ic_growth_model.fit(X_train, y_ic_train)

            visc_pred = self.viscosity_model.predict(X_test)
            ic_pred = self.ic_growth_model.predict(X_test)

            visc_train_pred = self.viscosity_model.predict(X_train)
            ic_train_pred = self.ic_growth_model.predict(X_train)

            metrics = {
                'viscosity_r2_test': r2_score(y_visc_test, visc_pred),
                'viscosity_r2_train': r2_score(y_visc_train, visc_train_pred),
                'viscosity_rmse_test': float(np.sqrt(mean_squared_error(y_visc_test, visc_pred))),
                'viscosity_rmse_train': float(np.sqrt(mean_squared_error(y_visc_train, visc_train_pred))),
                'ic_growth_r2_test': r2_score(y_ic_test, ic_pred),
                'ic_growth_r2_train': r2_score(y_ic_train, ic_train_pred),
                'ic_growth_rmse_test': float(np.sqrt(mean_squared_error(y_ic_test, ic_pred))),
                'ic_growth_rmse_train': float(np.sqrt(mean_squared_error(y_ic_train, ic_train_pred))),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'total_samples': len(X)
            }

            self._save_models()

            return {
                'success': True,
                'metrics': metrics,
                'feature_importance': {
                    'viscosity': dict(zip(feature_names, self.viscosity_model.feature_importances_)),
                    'ic_growth': dict(zip(feature_names, self.ic_growth_model.feature_importances_))
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Training failed: {str(e)}',
                'sklearn_available': self.sklearn_available
            }

    def get_feature_importance(self) -> Dict[str, Any]:
        if not self.sklearn_available:
            return {
                'success': False,
                'message': 'scikit-learn not available',
                'sklearn_available': False
            }

        if self.viscosity_model is None or self.ic_growth_model is None:
            return {
                'success': False,
                'message': 'Models not trained yet. Call train() first.',
                'is_trained': False
            }

        feature_names = self.feature_names
        visc_importance = self.viscosity_model.feature_importances_
        ic_importance = self.ic_growth_model.feature_importances_

        visc_ranked = sorted(
            zip(feature_names, visc_importance),
            key=lambda x: x[1],
            reverse=True
        )
        ic_ranked = sorted(
            zip(feature_names, ic_importance),
            key=lambda x: x[1],
            reverse=True
        )

        top_5_visc = [{'feature': f, 'importance': float(i)} for f, i in visc_ranked[:5]]
        top_5_ic = [{'feature': f, 'importance': float(i)} for f, i in ic_ranked[:5]]

        feature_categories = {
            'basic_parameters': [
                'core_radius', 'thermal_expansion', 'icb_heat_flux', 'cmb_heat_flux',
                'inner_core_radius', 'inner_core_volume_ratio', 'outer_core_thickness',
                'heat_flux_partition'
            ],
            'magnetic_properties': [
                'dipole_moment', 'dipole_tilt', 'magnetic_energy',
                'magnetic_to_kinetic_ratio', 'energy_per_dipole'
            ],
            'dimensionless_numbers': [
                'rayleigh_number', 'prandtl_number', 'magnetic_reynolds_number',
                'ekman_number', 'ra_pr_product', 'ra_pr_ratio', 'ra_sqrt', 'pr_log'
            ],
            'reversal_dynamics': [
                'polarity_reversal_count', 'polarity_reversal_rate',
                'reversal_rate_per_magnetic_time', 'energy_per_reversal'
            ],
            'energy_efficiency': [
                'kinetic_energy', 'magnetic_energy_generation_efficiency',
                'relaxation_time', 'dynamo_efficiency'
            ]
        }

        category_importance = {}
        for category, feats in feature_categories.items():
            visc_total = sum(float(visc_importance[feature_names.index(f)])
                            for f in feats if f in feature_names)
            ic_total = sum(float(ic_importance[feature_names.index(f)])
                          for f in feats if f in feature_names)
            category_importance[category] = {
                'viscosity_importance': visc_total,
                'ic_growth_importance': ic_total
            }

        return {
            'success': True,
            'is_trained': True,
            'feature_importance': {
                'viscosity': dict(zip(feature_names, [float(i) for i in visc_importance])),
                'ic_growth': dict(zip(feature_names, [float(i) for i in ic_importance]))
            },
            'top_features': {
                'viscosity': top_5_visc,
                'ic_growth': top_5_ic
            },
            'category_importance': category_importance,
            'model_info': {
                'viscosity_model_type': type(self.viscosity_model).__name__,
                'ic_growth_model_type': type(self.ic_growth_model).__name__,
                'n_features': len(feature_names),
                'feature_names': feature_names
            }
        }

    def _get_paleomagnetic_features(
        self,
        target_record: Dict[str, Any]
    ) -> np.ndarray:
        feature_names = [
            'core_radius', 'thermal_expansion', 'icb_heat_flux',
            'cmb_heat_flux', 'inner_core_radius',
            'dipole_moment', 'dipole_tilt', 'magnetic_energy',
            'kinetic_energy', 'polarity_reversal_count',
            'magnetic_energy_generation_efficiency', 'relaxation_time',
            'rayleigh_number', 'prandtl_number', 'magnetic_reynolds_number', 'ekman_number',
            'ra_pr_product', 'ra_pr_ratio', 'ra_sqrt', 'pr_log',
            'polarity_reversal_rate', 'reversal_rate_per_magnetic_time',
            'magnetic_to_kinetic_ratio', 'energy_per_dipole', 'energy_per_reversal',
            'dynamo_efficiency', 'inner_core_volume_ratio', 'outer_core_thickness',
            'heat_flux_partition'
        ]

        default_values = {
            'core_radius': PhysicalConstants.CORE_RADIUS,
            'thermal_expansion': PhysicalConstants.THERMAL_EXPANSION,
            'icb_heat_flux': 0.1,
            'cmb_heat_flux': 0.05,
            'inner_core_radius': PhysicalConstants.CURRENT_INNER_CORE_RADIUS,
            'dipole_moment': PhysicalConstants.CURRENT_DIPOLE_MOMENT,
            'dipole_tilt': 10.0,
            'magnetic_energy': 1e25,
            'kinetic_energy': 1e22,
            'polarity_reversal_count': 0,
            'magnetic_energy_generation_efficiency': 0.01,
            'relaxation_time': 1e12,
            'rayleigh_number': 1e8,
            'prandtl_number': 1.0,
            'magnetic_reynolds_number': 100.0,
            'ekman_number': 1e-15
        }

        raw_features = {}
        for feat in feature_names[:16]:
            raw_features[feat] = float(target_record.get(feat, default_values.get(feat, 0.0)))

        geological_age = float(target_record.get('geological_age', 0.0))
        if geological_age > 0:
            age_factor = max(0.0, 1.0 - geological_age / PhysicalConstants.EARTH_AGE)
            icb_enhancement = 1.0 + 2.0 * age_factor
            raw_features['icb_heat_flux'] *= icb_enhancement

            if geological_age > PhysicalConstants.INNER_CORE_FORMATION_AGE:
                raw_features['inner_core_radius'] = 0.0
            else:
                ic_scaling = (1.0 - geological_age / PhysicalConstants.INNER_CORE_FORMATION_AGE) ** 0.5
                raw_features['inner_core_radius'] *= ic_scaling

        reversal_frequency = float(target_record.get('reversal_frequency', 0.01))
        raw_features['polarity_reversal_rate'] = reversal_frequency

        dipole_moment = raw_features['dipole_moment']
        rayleigh = raw_features['rayleigh_number']
        prandtl = raw_features['prandtl_number']
        magnetic_reynolds = raw_features['magnetic_reynolds_number']
        ekman = raw_features['ekman_number']

        raw_features['ra_pr_product'] = rayleigh * prandtl
        raw_features['ra_pr_ratio'] = rayleigh / max(prandtl, 1e-10)
        raw_features['ra_sqrt'] = np.sqrt(max(rayleigh, 0.0))
        raw_features['pr_log'] = np.log10(max(prandtl, 1e-10))

        raw_features['reversal_rate_per_magnetic_time'] = reversal_frequency * max(magnetic_reynolds, 1.0)

        if raw_features['kinetic_energy'] > 0:
            raw_features['magnetic_to_kinetic_ratio'] = raw_features['magnetic_energy'] / max(raw_features['kinetic_energy'], 1e-10)
        else:
            raw_features['magnetic_to_kinetic_ratio'] = 0.0

        if dipole_moment > 0:
            raw_features['energy_per_dipole'] = raw_features['magnetic_energy'] / max(dipole_moment, 1e-10)
        else:
            raw_features['energy_per_dipole'] = 0.0

        if raw_features['polarity_reversal_count'] > 0:
            raw_features['energy_per_reversal'] = raw_features['magnetic_energy'] / max(raw_features['polarity_reversal_count'], 1)
        else:
            raw_features['energy_per_reversal'] = raw_features['magnetic_energy']

        if magnetic_reynolds > 0:
            raw_features['dynamo_efficiency'] = raw_features['magnetic_energy_generation_efficiency'] * np.sqrt(max(magnetic_reynolds, 0.0))
        else:
            raw_features['dynamo_efficiency'] = raw_features['magnetic_energy_generation_efficiency']

        inner_core_ratio = raw_features['inner_core_radius'] / max(raw_features['core_radius'], 1e-10)
        raw_features['inner_core_volume_ratio'] = inner_core_ratio ** 3
        raw_features['outer_core_thickness'] = raw_features['core_radius'] - raw_features['inner_core_radius']

        total_heat_flux = raw_features['icb_heat_flux'] + raw_features['cmb_heat_flux']
        if total_heat_flux > 0:
            raw_features['heat_flux_partition'] = raw_features['icb_heat_flux'] / max(total_heat_flux, 1e-10)
        else:
            raw_features['heat_flux_partition'] = 0.5

        features = []
        for feat in feature_names:
            features.append(float(raw_features.get(feat, 0.0)))

        return np.array(features).reshape(1, -1)

    def _find_matching_simulations(
        self,
        target_features: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        completed_sims = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.COMPLETED
        ).all()

        feature_names = self.feature_names or [
            'core_radius', 'thermal_expansion', 'icb_heat_flux',
            'cmb_heat_flux', 'inner_core_radius',
            'dipole_moment', 'dipole_tilt', 'magnetic_energy',
            'kinetic_energy', 'polarity_reversal_count',
            'magnetic_energy_generation_efficiency', 'relaxation_time',
            'rayleigh_number', 'prandtl_number', 'magnetic_reynolds_number', 'ekman_number',
            'ra_pr_product', 'ra_pr_ratio', 'ra_sqrt', 'pr_log',
            'polarity_reversal_rate', 'reversal_rate_per_magnetic_time',
            'magnetic_to_kinetic_ratio', 'energy_per_dipole', 'energy_per_reversal',
            'dynamo_efficiency', 'inner_core_volume_ratio', 'outer_core_thickness',
            'heat_flux_partition'
        ]

        similarities = []
        for sim in completed_sims:
            engineered = self._engineer_features(sim)
            sim_features = []
            for feat in feature_names:
                val = engineered.get(feat, 0.0) or 0.0
                sim_features.append(float(val))
            sim_features = np.array(sim_features)

            if np.linalg.norm(target_features[0]) > 0 and np.linalg.norm(sim_features) > 0:
                similarity = np.dot(target_features[0], sim_features) / (
                    np.linalg.norm(target_features[0]) * np.linalg.norm(sim_features)
                )
            else:
                similarity = 0.0

            similarities.append({
                'simulation_id': sim.id,
                'name': sim.name,
                'similarity': float(similarity),
                'viscosity': sim.viscosity,
                'inner_core_radius': sim.inner_core_radius,
                'dipole_moment': sim.dipole_moment,
                'magnetic_energy': sim.total_magnetic_energy,
                'rayleigh_number': sim.rayleigh_number,
                'prandtl_number': sim.prandtl_number,
                'reversal_count': sim.polarity_reversal_count
            })

        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]

    def recommend(
        self,
        paleomagnetic_record: Dict[str, Any],
        top_k: int = 5
    ) -> Dict[str, Any]:
        target_features = self._get_paleomagnetic_features(paleomagnetic_record)
        matching_sims = self._find_matching_simulations(target_features, top_k)

        if not self.sklearn_available or self.viscosity_model is None or self.ic_growth_model is None:
            heuristic = HeuristicRecommendationEngine(self.db)
            result = heuristic.recommend_based_on_paleomagnetic_data(
                target_dipole_moment=paleomagnetic_record.get('dipole_moment', PhysicalConstants.CURRENT_DIPOLE_MOMENT),
                target_reversal_frequency=paleomagnetic_record.get('reversal_frequency', PhysicalConstants.CURRENT_REVERSAL_FREQUENCY),
                geological_age=paleomagnetic_record.get('geological_age', 0.0)
            )

            recommendation = Recommendation(
                target_paleomagnetic_record=paleomagnetic_record.get('name', 'Unknown Record'),
                recommended_viscosity=result['recommended_viscosity'],
                recommended_inner_core_growth_rate=result['recommended_inner_core_growth_rate'],
                confidence_score=result['confidence_score'],
                matching_simulations=matching_sims,
                used_features=self.feature_names or [
                    'core_radius', 'thermal_expansion', 'icb_heat_flux', 'cmb_heat_flux',
                    'inner_core_radius', 'dipole_moment', 'reversal_frequency',
                    'rayleigh_number', 'prandtl_number', 'polarity_reversal_rate',
                    'dynamo_efficiency'
                ],
                model_version='heuristic-2.0.0'
            )
            self.db.add(recommendation)
            self.db.commit()

            return {
                'success': True,
                'recommended_viscosity': result['recommended_viscosity'],
                'recommended_inner_core_growth_rate': result['recommended_inner_core_growth_rate'],
                'confidence_score': result['confidence_score'],
                'matching_simulations': matching_sims,
                'used_features': self.feature_names or [],
                'model_version': 'heuristic-2.0.0',
                'recommendation_id': recommendation.id,
                'paleomagnetic_record': paleomagnetic_record,
                'note': 'Using heuristic engine (scikit-learn not available or insufficient training data)',
                'physical_model': result.get('physical_model'),
                'scaling_relations': result.get('scaling_relations')
            }

        if self.scaler:
            target_scaled = self.scaler.transform(target_features)
        else:
            target_scaled = target_features

        recommended_viscosity = float(self.viscosity_model.predict(target_scaled)[0])
        recommended_ic_growth = float(self.ic_growth_model.predict(target_scaled)[0])

        visc_std = np.std([tree.predict(target_scaled)[0]
                           for tree in self.viscosity_model.estimators_])
        ic_std = np.std([tree.predict(target_scaled)[0]
                         for tree in self.ic_growth_model.estimators_])

        confidence_visc = max(0.0, min(1.0, 1.0 - visc_std / max(recommended_viscosity, 1e-10)))
        confidence_ic = max(0.0, min(1.0, 1.0 - ic_std / max(recommended_ic_growth, 1e-10)))
        confidence_score = 0.5 * (confidence_visc + confidence_ic)

        recommendation = Recommendation(
            target_paleomagnetic_record=paleomagnetic_record.get('name', 'Unknown Record'),
            recommended_viscosity=recommended_viscosity,
            recommended_inner_core_growth_rate=recommended_ic_growth,
            confidence_score=confidence_score,
            matching_simulations=matching_sims,
            used_features=self.feature_names,
            model_version='ml-2.0.0'
        )
        self.db.add(recommendation)
        self.db.commit()

        feature_importance = self.get_feature_importance()

        return {
            'success': True,
            'recommended_viscosity': recommended_viscosity,
            'recommended_inner_core_growth_rate': recommended_ic_growth,
            'confidence_score': confidence_score,
            'confidence_components': {
                'viscosity_confidence': confidence_visc,
                'ic_growth_confidence': confidence_ic,
                'viscosity_std': float(visc_std),
                'ic_growth_std': float(ic_std)
            },
            'matching_simulations': matching_sims,
            'used_features': self.feature_names,
            'model_version': 'ml-2.0.0',
            'recommendation_id': recommendation.id,
            'paleomagnetic_record': paleomagnetic_record,
            'feature_importance': feature_importance.get('feature_importance', {}) if feature_importance.get('success') else None
        }

    def get_recommendations(self, limit: int = 10) -> List[Recommendation]:
        return self.db.query(Recommendation).order_by(
            Recommendation.created_at.desc()
        ).limit(limit).all()

    def get_recommendation_by_id(self, recommendation_id: int) -> Optional[Recommendation]:
        return self.db.query(Recommendation).filter(
            Recommendation.id == recommendation_id
        ).first()

    def get_model_info(self) -> Dict[str, Any]:
        X, y_visc, y_ic, feature_names = self._collect_training_data()

        return {
            'is_trained': self.viscosity_model is not None and self.ic_growth_model is not None,
            'total_training_samples': len(X),
            'feature_names': feature_names,
            'n_features': len(feature_names),
            'viscosity_model_type': type(self.viscosity_model).__name__ if self.viscosity_model else None,
            'ic_growth_model_type': type(self.ic_growth_model).__name__ if self.ic_growth_model else None,
            'model_version': '2.0.0',
            'scaler_available': self.scaler is not None,
            'sklearn_available': self.sklearn_available
        }

    def recommend_based_on_paleomagnetic_data(
        self,
        simulation_id: int,
        target_dipole_moment: float = None,
        target_reversal_frequency: float = None,
        paleomagnetic_age_ma: float = 0.0
    ) -> Dict[str, Any]:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            return {'success': False, 'message': 'Simulation not found'}

        heuristic = HeuristicRecommendationEngine(self.db)
        result = heuristic.recommend_based_on_paleomagnetic_data(
            target_dipole_moment=target_dipole_moment or sim.dipole_moment or PhysicalConstants.CURRENT_DIPOLE_MOMENT,
            target_reversal_frequency=target_reversal_frequency or 0.01,
            geological_age=paleomagnetic_age_ma
        )

        paleo_record = {
            'name': f'Paleomagnetic match for sim_{simulation_id}',
            'dipole_moment': target_dipole_moment,
            'reversal_frequency': target_reversal_frequency,
            'geological_age': paleomagnetic_age_ma
        }

        target_features = self._get_paleomagnetic_features(paleo_record)
        matching_sims = self._find_matching_simulations(target_features, top_k=5)

        recommendation = Recommendation(
            target_paleomagnetic_record=paleo_record.get('name', 'Unknown Record'),
            recommended_viscosity=result['recommended_viscosity'],
            recommended_inner_core_growth_rate=result['recommended_inner_core_growth_rate'],
            confidence_score=result['confidence_score'],
            matching_simulations=matching_sims,
            used_features=self.feature_names or [],
            model_version='heuristic-2.0.0'
        )
        self.db.add(recommendation)
        self.db.commit()

        return {
            'success': True,
            'engine_type': 'heuristic' if not self.sklearn_available else 'hybrid',
            'recommended_viscosity': result['recommended_viscosity'],
            'recommended_ic_radius': result.get('recommended_inner_core_radius', sim.inner_core_radius or PhysicalConstants.CURRENT_INNER_CORE_RADIUS),
            'recommended_growth_rate': result['recommended_inner_core_growth_rate'],
            'match_score': result['confidence_score'],
            'confidence_score': result['confidence_score'],
            'matching_simulations': matching_sims,
            'physical_model': result.get('physical_model'),
            'scaling_relations': result.get('scaling_relations'),
            'recommendation_id': recommendation.id,
            'note': 'Using physical scaling relations'
        }


class HeuristicRecommendationEngine:
    def __init__(self, db: Session):
        self.db = db

    def _calculate_inner_core_radius(self, geological_age: float) -> float:
        if geological_age >= PhysicalConstants.INNER_CORE_FORMATION_AGE:
            return 0.0

        normalized_age = geological_age / PhysicalConstants.INNER_CORE_FORMATION_AGE
        ic_radius = PhysicalConstants.CURRENT_INNER_CORE_RADIUS * np.sqrt(1.0 - normalized_age)

        return float(ic_radius)

    def _calculate_viscosity_from_age(self, geological_age: float, ic_radius: float) -> float:
        current_ic_r = PhysicalConstants.CURRENT_INNER_CORE_RADIUS
        current_visc = PhysicalConstants.CURRENT_VISCOSITY

        if ic_radius <= 0:
            return current_visc * 0.01

        visc_scaling_exponent = 2.5
        visc = current_visc * (ic_radius / current_ic_r) ** visc_scaling_exponent

        if geological_age > PhysicalConstants.INNER_CORE_FORMATION_AGE:
            pre_ic_visc = current_visc * 0.005
            age_factor = (geological_age - PhysicalConstants.INNER_CORE_FORMATION_AGE) / \
                         (PhysicalConstants.EARTH_AGE - PhysicalConstants.INNER_CORE_FORMATION_AGE)
            visc = pre_ic_visc * (0.5 + 0.5 * age_factor)

        return float(visc)

    def _calculate_ic_growth_rate(self, geological_age: float, ic_radius: float) -> float:
        if geological_age >= PhysicalConstants.INNER_CORE_FORMATION_AGE:
            ic_age = 0.0
        else:
            ic_age = PhysicalConstants.INNER_CORE_FORMATION_AGE - geological_age

        tau = 3e8
        initial_growth_rate = 5e-11
        current_growth_rate = PhysicalConstants.CURRENT_IC_GROWTH_RATE

        if ic_age <= 0:
            growth_rate = current_growth_rate
        else:
            growth_rate = initial_growth_rate * np.exp(-ic_age / tau) + \
                          current_growth_rate * (1.0 - np.exp(-ic_age / tau))

        if ic_radius <= 0:
            growth_rate = initial_growth_rate

        return float(growth_rate)

    def _apply_dipole_moment_scaling(
        self,
        base_viscosity: float,
        target_dipole_moment: float,
        reference_dipole: float
    ) -> float:
        dipole_ratio = target_dipole_moment / max(reference_dipole, 1e-10)

        scaling_exponent = -2.0
        visc = base_viscosity * (dipole_ratio ** scaling_exponent)

        min_visc = 1e-6
        max_visc = 1e0
        visc = max(min_visc, min(max_visc, visc))

        return float(visc)

    def _apply_reversal_frequency_scaling(
        self,
        base_viscosity: float,
        target_reversal_frequency: float,
        reference_frequency: float
    ) -> float:
        if target_reversal_frequency <= 0 or reference_frequency <= 0:
            return base_viscosity

        reversal_ratio = target_reversal_frequency / reference_frequency

        scaling_exponent = -0.8
        visc = base_viscosity * (reversal_ratio ** scaling_exponent)

        min_visc = 1e-6
        max_visc = 1e0
        visc = max(min_visc, min(max_visc, visc))

        return float(visc)

    def _calculate_rayleigh_from_viscosity(
        self,
        viscosity: float,
        core_radius: float = PhysicalConstants.CORE_RADIUS
    ) -> float:
        nu = viscosity / PhysicalConstants.DENSITY
        delta_T = 1000.0

        Ra = (PhysicalConstants.GRAVITY * PhysicalConstants.THERMAL_EXPANSION *
              delta_T * core_radius**3) / (nu * PhysicalConstants.THERMAL_DIFFUSIVITY)

        return float(Ra)

    def _calculate_confidence(
        self,
        geological_age: float,
        target_dipole_moment: float,
        target_reversal_frequency: float,
        matching_sims: List[Dict[str, Any]]
    ) -> float:
        base_confidence = 0.5

        age_factor = 1.0 - min(1.0, geological_age / PhysicalConstants.EARTH_AGE)
        age_weight = 0.2 * age_factor

        dipole_ratio = min(target_dipole_moment, PhysicalConstants.CURRENT_DIPOLE_MOMENT * 2.0) / \
                       max(PhysicalConstants.CURRENT_DIPOLE_MOMENT, 1e-10)
        dipole_deviation = abs(dipole_ratio - 1.0)
        dipole_weight = 0.15 * (1.0 - min(1.0, dipole_deviation))

        reversal_ratio = min(target_reversal_frequency, 0.1) / max(PhysicalConstants.CURRENT_REVERSAL_FREQUENCY, 1e-10)
        reversal_deviation = abs(np.log10(max(reversal_ratio, 1e-3)))
        reversal_weight = 0.15 * max(0.0, 1.0 - reversal_deviation / 2.0)

        if matching_sims and len(matching_sims) > 0:
            best_similarity = matching_sims[0].get('similarity', 0.0)
            data_weight = 0.25 * best_similarity
        else:
            data_weight = 0.0

        if len(matching_sims) >= 3:
            coverage_weight = 0.25
        elif len(matching_sims) >= 1:
            coverage_weight = 0.1 * len(matching_sims)
        else:
            coverage_weight = 0.0

        confidence = base_confidence + age_weight + dipole_weight + \
                     reversal_weight + data_weight + coverage_weight

        return float(max(0.1, min(0.95, confidence)))

    def recommend_based_on_paleomagnetic_data(
        self,
        target_dipole_moment: float = 8.0e22,
        target_reversal_frequency: float = 0.01,
        geological_age: float = 0.0
    ) -> Dict[str, Any]:
        ic_radius = self._calculate_inner_core_radius(geological_age)

        base_viscosity = self._calculate_viscosity_from_age(geological_age, ic_radius)

        viscosity = self._apply_dipole_moment_scaling(
            base_viscosity,
            target_dipole_moment,
            PhysicalConstants.CURRENT_DIPOLE_MOMENT
        )

        viscosity = self._apply_reversal_frequency_scaling(
            viscosity,
            target_reversal_frequency,
            PhysicalConstants.CURRENT_REVERSAL_FREQUENCY
        )

        ic_growth_rate = self._calculate_ic_growth_rate(geological_age, ic_radius)

        completed_sims = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.COMPLETED
        ).all()

        matching = []
        for sim in completed_sims:
            if sim.dipole_moment and sim.polarity_reversal_count is not None:
                dipole_diff = abs(sim.dipole_moment - target_dipole_moment) / max(target_dipole_moment, 1e-10)
                reversal_rate = sim.polarity_reversal_count / max(sim.current_iteration, 1)
                reversal_diff = abs(reversal_rate - target_reversal_frequency) / max(target_reversal_frequency, 1e-10)
                score = 1.0 / (1.0 + dipole_diff + reversal_diff)

                matching.append({
                    'simulation_id': sim.id,
                    'name': sim.name,
                    'match_score': float(score),
                    'viscosity': sim.viscosity,
                    'inner_core_radius': sim.inner_core_radius,
                    'dipole_moment': sim.dipole_moment,
                    'reversal_count': sim.polarity_reversal_count,
                    'rayleigh_number': sim.rayleigh_number,
                    'prandtl_number': sim.prandtl_number
                })

        matching.sort(key=lambda x: x['match_score'], reverse=True)
        matching_top = matching[:5]

        confidence_score = self._calculate_confidence(
            geological_age,
            target_dipole_moment,
            target_reversal_frequency,
            matching_top
        )

        rayleigh_number = self._calculate_rayleigh_from_viscosity(viscosity)

        return {
            'recommended_viscosity': float(viscosity),
            'recommended_inner_core_growth_rate': float(ic_growth_rate),
            'confidence_score': float(confidence_score),
            'matching_simulations': matching_top,
            'method': 'heuristic_physical_model',
            'physical_model': {
                'inner_core_radius': float(ic_radius),
                'rayleigh_number': float(rayleigh_number),
                'pre_inner_core': geological_age >= PhysicalConstants.INNER_CORE_FORMATION_AGE,
                'inner_core_age': float(max(0.0, PhysicalConstants.INNER_CORE_FORMATION_AGE - geological_age))
            },
            'scaling_relations': {
                'viscosity_age_scaling': r'\nu \propto r_{ic}^{2.5}',
                'viscosity_dipole_scaling': r'\nu \propto \mu^{-2}',
                'viscosity_reversal_scaling': r'\nu \propto f^{-0.8}',
                'ic_growth_time_decay': r'dr_{ic}/dt \propto e^{-t/\tau}',
                'rayleigh_number': r'Ra = g \alpha \Delta T L^3 / (\nu \kappa)'
            }
        }

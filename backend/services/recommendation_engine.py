import numpy as np
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
import pickle

from sqlalchemy.orm import Session

from backend.models import Simulation, Recommendation, SimulationStatus


class RecommendationEngine:
    def __init__(self, db: Session, model_dir: str = './models'):
        self.db = db
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

        self.viscosity_model: Optional[RandomForestRegressor] = None
        self.ic_growth_model: Optional[GradientBoostingRegressor] = None
        self.scaler: Optional[StandardScaler] = None
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
            'magnetic_energy_generation_efficiency', 'relaxation_time'
        ]

        for sim in completed_sims:
            if sim.viscosity is None or sim.inner_core_radius is None:
                continue

            row = []
            for feat in feature_names:
                val = getattr(sim, feat, None)
                if val is None:
                    val = 0.0
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
                'message': f'Insufficient training data: {len(X)} samples (minimum 10 required)'
            }

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        X_train, X_test, y_visc_train, y_visc_test = train_test_split(
            X_scaled, y_visc, test_size=test_size, random_state=42
        )
        _, _, y_ic_train, y_ic_test = train_test_split(
            X_scaled, y_ic, test_size=test_size, random_state=42
        )

        self.viscosity_model = RandomForestRegressor(
            n_estimators=100, max_depth=15, random_state=42
        )
        self.viscosity_model.fit(X_train, y_visc_train)

        self.ic_growth_model = GradientBoostingRegressor(
            n_estimators=100, max_depth=8, learning_rate=0.1, random_state=42
        )
        self.ic_growth_model.fit(X_train, y_ic_train)

        visc_pred = self.viscosity_model.predict(X_test)
        ic_pred = self.ic_growth_model.predict(X_test)

        metrics = {
            'viscosity_r2': r2_score(y_visc_test, visc_pred),
            'viscosity_rmse': np.sqrt(mean_squared_error(y_visc_test, visc_pred)),
            'ic_growth_r2': r2_score(y_ic_test, ic_pred),
            'ic_growth_rmse': np.sqrt(mean_squared_error(y_ic_test, ic_pred)),
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

    def _get_paleomagnetic_features(
        self,
        target_record: Dict[str, Any]
    ) -> np.ndarray:
        feature_names = [
            'core_radius', 'thermal_expansion', 'icb_heat_flux',
            'cmb_heat_flux', 'inner_core_radius',
            'dipole_moment', 'dipole_tilt', 'magnetic_energy',
            'kinetic_energy', 'polarity_reversal_count',
            'magnetic_energy_generation_efficiency', 'relaxation_time'
        ]

        default_values = {
            'core_radius': 3.48e6,
            'thermal_expansion': 1e-5,
            'icb_heat_flux': 0.1,
            'cmb_heat_flux': 0.05,
            'inner_core_radius': 1.22e6,
            'dipole_moment': 8.0e22,
            'dipole_tilt': 10.0,
            'magnetic_energy': 1e25,
            'kinetic_energy': 1e22,
            'polarity_reversal_count': 0,
            'magnetic_energy_generation_efficiency': 0.01,
            'relaxation_time': 1e12
        }

        features = []
        for feat in feature_names:
            val = target_record.get(feat, default_values.get(feat, 0.0))
            features.append(float(val))

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
            'magnetic_energy_generation_efficiency', 'relaxation_time'
        ]

        similarities = []
        for sim in completed_sims:
            sim_features = []
            for feat in feature_names:
                val = getattr(sim, feat, 0.0) or 0.0
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
                'magnetic_energy': sim.total_magnetic_energy
            })

        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]

    def recommend(
        self,
        paleomagnetic_record: Dict[str, Any],
        top_k: int = 5
    ) -> Dict[str, Any]:
        if self.viscosity_model is None or self.ic_growth_model is None:
            train_result = self.train()
            if not train_result.get('success', False):
                return {
                    'success': False,
                    'message': 'Model training failed. Using heuristic recommendations.',
                    'recommended_viscosity': 1e-2,
                    'recommended_inner_core_growth_rate': 1e-12,
                    'confidence_score': 0.5,
                    'matching_simulations': [],
                    'used_features': []
                }

        target_features = self._get_paleomagnetic_features(paleomagnetic_record)

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

        matching_sims = self._find_matching_simulations(target_features, top_k)

        recommendation = Recommendation(
            target_paleomagnetic_record=paleomagnetic_record.get('name', 'Unknown Record'),
            recommended_viscosity=recommended_viscosity,
            recommended_inner_core_growth_rate=recommended_ic_growth,
            confidence_score=confidence_score,
            matching_simulations=matching_sims,
            used_features=self.feature_names,
            model_version='1.0.0'
        )
        self.db.add(recommendation)
        self.db.commit()

        return {
            'success': True,
            'recommended_viscosity': recommended_viscosity,
            'recommended_inner_core_growth_rate': recommended_ic_growth,
            'confidence_score': confidence_score,
            'matching_simulations': matching_sims,
            'used_features': self.feature_names,
            'model_version': '1.0.0',
            'recommendation_id': recommendation.id,
            'paleomagnetic_record': paleomagnetic_record
        }

    def get_recommendations(self, limit: int = 10) -> List[Recommendation]:
        return self.db.query(Recommendation).order_by(
            Recommendation.created_at.desc()
        ).limit(limit).all()

    def get_model_info(self) -> Dict[str, Any]:
        X, y_visc, y_ic, feature_names = self._collect_training_data()

        return {
            'is_trained': self.viscosity_model is not None and self.ic_growth_model is not None,
            'total_training_samples': len(X),
            'feature_names': feature_names,
            'viscosity_model_type': type(self.viscosity_model).__name__ if self.viscosity_model else None,
            'ic_growth_model_type': type(self.ic_growth_model).__name__ if self.ic_growth_model else None,
            'model_version': '1.0.0'
        }


class HeuristicRecommendationEngine:
    def __init__(self, db: Session):
        self.db = db

    def recommend_based_on_paleomagnetic_data(
        self,
        target_dipole_moment: float = 8.0e22,
        target_reversal_frequency: float = 0.01,
        geological_age: float = 0.0
    ) -> Dict[str, Any]:
        age_factor = np.exp(-geological_age / 1e9)

        if geological_age < 1e8:
            base_viscosity = 1e-2
            base_ic_growth = 1e-12
        elif geological_age < 1e9:
            base_viscosity = 5e-3
            base_ic_growth = 5e-12
        else:
            base_viscosity = 1e-3
            base_ic_growth = 1e-11

        dipole_factor = target_dipole_moment / 8.0e22
        reversal_factor = target_reversal_frequency / 0.01

        recommended_viscosity = base_viscosity * np.sqrt(dipole_factor) / reversal_factor
        recommended_ic_growth = base_ic_growth * age_factor * np.sqrt(reversal_factor)

        completed_sims = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.COMPLETED
        ).all()

        matching = []
        for sim in completed_sims:
            if sim.dipole_moment and sim.polarity_reversal_count is not None:
                dipole_diff = abs(sim.dipole_moment - target_dipole_moment) / target_dipole_moment
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
                    'reversal_count': sim.polarity_reversal_count
                })

        matching.sort(key=lambda x: x['match_score'], reverse=True)

        return {
            'recommended_viscosity': float(recommended_viscosity),
            'recommended_inner_core_growth_rate': float(recommended_ic_growth),
            'confidence_score': 0.6,
            'matching_simulations': matching[:5],
            'method': 'heuristic',
            'age_factor': float(age_factor),
            'dipole_factor': float(dipole_factor),
            'reversal_factor': float(reversal_factor)
        }

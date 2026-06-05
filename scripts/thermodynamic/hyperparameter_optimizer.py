# HyperparameterOptimizer - extracted from termo2.py
"""
NLP2CMD - Przykłady zastosowań w różnych dziedzinach.

Ten moduł zawiera praktyczne przykłady użycia NLP2CMD
w IT, nauce i biznesie.
"""
import asyncio
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
from hyperparameter_space import HyperparameterSpace

class HyperparameterOptimizer:
    """
    Optymalizator hiperparametrów używający Langevin sampling.

    Zamiast grid search czy random search, używamy
    termodynamicznego samplowania do eksploracji przestrzeni.
    """

    def __init__(self, space: HyperparameterSpace, n_samples: int = 20):
        self.space = space
        self.n_samples = n_samples

    def _decode_params(self, z: np.ndarray) -> dict:
        """Dekoduj wektor z do hiperparametrów."""
        # Sigmoid dla [0, 1], potem skaluj do zakresów
        sigmoid = lambda x: 1 / (1 + np.exp(-x))

        lr_range = self.space.learning_rate
        bs_range = self.space.batch_size

        return {
            'learning_rate': lr_range[0] + sigmoid(z[0]) * (lr_range[1] - lr_range[0]),
            'batch_size': int(bs_range[0] + sigmoid(z[1]) * (bs_range[1] - bs_range[0])),
            'num_layers': int(self.space.num_layers[0] + sigmoid(z[2]) *
                              (self.space.num_layers[1] - self.space.num_layers[0])),
            'dropout': sigmoid(z[3]) * self.space.dropout[1],
            'hidden_dim': int(self.space.hidden_dim[0] + sigmoid(z[4]) *
                              (self.space.hidden_dim[1] - self.space.hidden_dim[0])),
        }

    def _evaluate(self, params: dict) -> float:
        """Symulacja ewaluacji modelu (w produkcji - prawdziwy trening)."""
        # Symulacja: optymalne wartości gdzieś w środku
        optimal = {
            'learning_rate': 0.001,
            'batch_size': 64,
            'num_layers': 4,
            'dropout': 0.2,
            'hidden_dim': 256,
        }

        # "Loss" jako odległość od optimum
        loss = 0.0
        loss += abs(np.log(params['learning_rate']) - np.log(optimal['learning_rate']))
        loss += abs(params['batch_size'] - optimal['batch_size']) / 100
        loss += abs(params['num_layers'] - optimal['num_layers'])
        loss += abs(params['dropout'] - optimal['dropout']) * 5
        loss += abs(params['hidden_dim'] - optimal['hidden_dim']) / 100

        return loss + np.random.normal(0, 0.1)  # Dodaj szum

    def optimize(self) -> tuple[dict, float]:
        """Znajdź optymalne hiperparametry."""
        best_params = None
        best_loss = float('inf')

        # Prosty Langevin sampling
        z = np.random.randn(5)

        for i in range(self.n_samples):
            params = self._decode_params(z)
            loss = self._evaluate(params)

            if loss < best_loss:
                best_loss = loss
                best_params = params

            # Langevin update (uproszczony)
            grad = np.random.randn(5) * 0.1  # Przybliżony gradient
            z = z - 0.1 * grad + np.sqrt(0.2) * np.random.randn(5)

        return best_params, best_loss

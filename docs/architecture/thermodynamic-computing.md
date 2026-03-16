# Thermodynamic Computing Architecture

## Overview

System termodynamiczny w NLP2CMD implementuje energo-optymalne generowanie komend wykorzystując:
- **Langevin Dynamics** - fizykę statystyczną do próbkowania rozwiązań
- **Energy-Based Models** - modele energii do oceny jakości
- **Entropy Production** - regularyzację entropii dla stabilności

## Core Concepts

### Energy-Based Models (EBM)

Funkcja energii ocenia jakość rozwiązania:

```python
E(x) = Σ constraints(x) + Σ preferences(x)
```

Niskie energia = lepsze rozwiązanie.

### Langevin Sampling

Probabilistyczne przeszukiwanie przestrzeni rozwiązań:

```python
dx = -∇E(x)dt + √(2T)dW
```

Gdzie:
- `∇E(x)` - gradient energii (kierunek optymalizacji)
- `T` - temperatura (eksploracja vs eksploatacja)
- `dW` - szum Wienera (stochasticity)

### Entropy Production

Regularyzacja zapobiegająca przedwczesnej zbieżności:

```
ΔS = Q/T ≥ 0  (druga zasada termodynamiki)
```

## Components

### 1. Energy Models

**QuadraticEnergyModel** - proste zależności kwadratowe
```python
from nlp2cmd.thermodynamic.energy_models import QuadraticEnergyModel

model = QuadraticEnergyModel(
    constraints={
        'memory': {'target': 16, 'weight': 1.0},
        'cpu': {'target': 8, 'weight': 0.8}
    }
)
```

**ConstraintEnergyModel** - twarde ograniczenia
```python
from nlp2cmd.thermodynamic.energy_models import ConstraintEnergyModel

model = ConstraintEnergyModel(
    constraints=[
        lambda x: x['cpu'] <= 16,  # hard constraint
        lambda x: x['memory'] >= 8
    ]
)
```

### 2. Langevin Sampler

```python
from nlp2cmd.thermodynamic.sampler import LangevinSampler

sampler = LangevinSampler(
    energy_model=model,
    temperature=1.0,
    dt=0.01,
    n_steps=1000
)

solution = sampler.sample(initial_state)
```

### 3. Thermodynamic Router

```python
from nlp2cmd.thermodynamic.router import ThermodynamicRouter

router = ThermodynamicRouter(
    energy_models={
        'scheduling': SchedulingEnergyModel(),
        'allocation': AllocationEnergyModel(),
        'routing': RoutingEnergyModel()
    }
)

result = router.route(problem_type, constraints)
```

### 4. Majority Voter

Agregacja wyników z wielu sample'ów:
- **Energy voting** - wybór o najniższej energii
- **Entropy voting** - maksymalizacja entropii (różnorodność)
- **Cluster voting** - grupowanie podobnych rozwiązań

```python
from nlp2cmd.thermodynamic.voter import MajorityVoter

voter = MajorityVoter(strategy='energy')
consensus = voter.vote(samples)
```

## Use Cases

### 1. Drug Discovery (Lead Optimization)

Wielokryterialna optymalizacja cząsteczki:
- binding affinity
- ADMET properties
- syntetyczna dostępność

**Benefits:**
- 45-57% mniejsze zużycie energii vs LLM-only
- Równoczesna optymalizacja wielu kryteriów

### 2. Healthcare Scheduling

Harmonogramowanie sal operacyjnych i personelu:
- ograniczenia czasu sterylizacji
- równoważenie obciążenia
- priorytety pacjentów

### 3. Resource Allocation

Alokacja zasobów cloudowych:
- CPU, memory, storage constraints
- koszt vs wydajność
- SLA requirements

## Performance Characteristics

| Metryka | Standard | Thermodynamic | Improvement |
|---------|----------|---------------|-------------|
| Energy efficiency | Baseline | **+45-57%** | Mniejsze zużycie |
| Multi-objective | Sekwencyjne | **Równoległe** | Szybsze |
| Exploration | Lokalna | **Globalna** | Lepsza jakość |
| Convergence | Szybka/utknięcie | **Stabilna** | Niezawodna |

## Integration with NLP2CMD

```python
from nlp2cmd import NLP2CMD
from nlp2cmd.thermodynamic import ThermodynamicRouter

# Standard pipeline
nlp = NLP2CMD()

# With thermodynamic optimization
nlp_thermo = NLP2CMD(
    router=ThermodynamicRouter()
)

# Optimize resource allocation
result = nlp_thermo.transform(
    "Znajdź optymalną alokację zasobów dla 3 VM",
    domain='allocation'
)
```

## Configuration

```python
thermo_config = {
    'temperature': 1.0,        # Eksploracja (wyższa = więcej)
    'dt': 0.01,                # Krok czasowy
    'n_steps': 1000,           # Iteracje sampling
    'n_samples': 10,           # Liczba próbek
    'voting_strategy': 'energy',
    'entropy_regularization': 0.1
}
```

## Scientific Background

### Primary Sources

- **Whitelam (2025)** - "Thermodynamic Computing for Optimization"
- **Langevin (1908)** - Równanie dynamiki
- **Boltzmann** - Rozkład energii

### Key Formulas

**Boltzmann Distribution:**
```
P(x) ∝ exp(-E(x)/kT)
```

**Free Energy:**
```
F = E - TS
```

**Entropy Production:**
```
ΔS = ∫ (dQ_rev/T)
```

## Future Directions

- **FPGA Backend** - Akceleracja sprzętowa
- **Analog Computing** - Fizyczne implementation
- **Federated Sampling** - Rozproszone obliczenia
- **Auto-Energy Model** - Automatyczne uczenie funkcji energii

## Related Documentation

- [API Reference](api/README.md) - Detailed API
- [Examples Guide](reference/examples-guide.md) - Practical examples
- [Thermodynamic Integration](../../THERMODYNAMIC_INTEGRATION.md) - Full integration guide

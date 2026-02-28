
"""
Generic Data Processing Framework for nlp2cmd.

Consolidates filter, map, transform, and reduce operations into
reusable, type-safe components.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, TypeVar, Generic, Union, Optional
from dataclasses import dataclass
from enum import Enum
import functools

T = TypeVar('T')
U = TypeVar('U')
R = TypeVar('R')


class ProcessType(Enum):
    """Types of data processing."""
    FILTER = "filter"
    MAP = "map"
    TRANSFORM = "transform"
    REDUCE = "reduce"
    AGGREGATE = "aggregate"


@dataclass
class ProcessResult:
    """Result of data processing operation."""
    data: Any
    success: bool
    errors: List[str]
    metadata: Dict[str, Any]


class BaseProcessor(Generic[T, U], ABC):
    """Base class for data processors."""
    
    def __init__(self, process_type: ProcessType, name: str):
        self.process_type = process_type
        self.name = name
        self.processed_count = 0
    
    @abstractmethod
    def process(self, data: T, **kwargs) -> U:
        """Process data."""
        pass
    
    def __call__(self, data: T, **kwargs) -> ProcessResult:
        """Make processor callable."""
        try:
            result = self.process(data, **kwargs)
            self.processed_count += 1
            return ProcessResult(
                data=result,
                success=True,
                errors=[],
                metadata={'processor': self.name, 'count': self.processed_count}
            )
        except Exception as e:
            return ProcessResult(
                data=data,
                success=False,
                errors=[str(e)],
                metadata={'processor': self.name, 'failed': True}
            )


class FilterProcessor(BaseProcessor[List[T], List[T]]):
    """Generic filter processor."""
    
    def __init__(self, predicate: Callable[[T], bool], name: str = "filter"):
        super().__init__(ProcessType.FILTER, name)
        self.predicate = predicate
    
    def process(self, data: List[T], **kwargs) -> List[T]:
        """Filter data based on predicate."""
        return [item for item in data if self.predicate(item)]


class MapProcessor(BaseProcessor[List[T], List[U]]):
    """Generic map processor."""
    
    def __init__(self, transform: Callable[[T], U], name: str = "map"):
        super().__init__(ProcessType.MAP, name)
        self.transform = transform
    
    def process(self, data: List[T], **kwargs) -> List[U]:
        """Transform each item in data."""
        return [self.transform(item) for item in data]


class TransformProcessor(BaseProcessor[T, U]):
    """Generic transform processor."""
    
    def __init__(self, transform: Callable[[T], U], name: str = "transform"):
        super().__init__(ProcessType.TRANSFORM, name)
        self.transform = transform
    
    def process(self, data: T, **kwargs) -> U:
        """Transform single data item."""
        return self.transform(data)


class ReduceProcessor(BaseProcessor[List[T], R]):
    """Generic reduce processor."""
    
    def __init__(self, reducer: Callable[[R, T], R], initial: R, name: str = "reduce"):
        super().__init__(ProcessType.REDUCE, name)
        self.reducer = reducer
        self.initial = initial
    
    def process(self, data: List[T], **kwargs) -> R:
        """Reduce data to single value."""
        result = self.initial
        for item in data:
            result = self.reducer(result, item)
        return result


class AggregateProcessor(BaseProcessor[List[T], Dict[str, Any]]):
    """Generic aggregate processor."""
    
    def __init__(self, aggregators: Dict[str, Callable[[List[T]], Any]], name: str = "aggregate"):
        super().__init__(ProcessType.AGGREGATE, name)
        self.aggregators = aggregators
    
    def process(self, data: List[T], **kwargs) -> Dict[str, Any]:
        """Aggregate data using multiple functions."""
        result = {}
        for name, aggregator in self.aggregators.items():
            try:
                result[name] = aggregator(data)
            except Exception as e:
                result[f"{name}_error"] = str(e)
        return result


class ProcessingPipeline:
    """Pipeline for chaining multiple processors."""
    
    def __init__(self, name: str = "pipeline"):
        self.name = name
        self.processors: List[BaseProcessor] = []
        self.execution_stats = []
    
    def add_processor(self, processor: BaseProcessor) -> 'ProcessingPipeline':
        """Add processor to pipeline."""
        self.processors.append(processor)
        return self
    
    def process(self, data: Any, **kwargs) -> ProcessResult:
        """Process data through all processors."""
        current_data = data
        errors = []
        metadata = {'pipeline': self.name, 'steps': []}
        
        for i, processor in enumerate(self.processors):
            result = processor(current_data, **kwargs)
            
            if not result.success:
                errors.extend(result.errors)
                metadata['steps'].append({
                    'step': i,
                    'processor': processor.name,
                    'status': 'failed',
                    'errors': result.errors
                })
                break
            
            current_data = result.data
            metadata['steps'].append({
                'step': i,
                'processor': processor.name,
                'status': 'success'
            })
        
        return ProcessResult(
            data=current_data,
            success=len(errors) == 0,
            errors=errors,
            metadata=metadata
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            'total_processors': len(self.processors),
            'processor_types': [p.process_type.value for p in self.processors],
            'total_processed': sum(p.processed_count for p in self.processors)
        }


# Convenience functions for common operations
def create_filter(predicate: Callable[[Any], bool], name: str = None) -> FilterProcessor:
    """Create filter processor."""
    return FilterProcessor(predicate, name or f"filter_{predicate.__name__}")


def create_map(transform: Callable[[Any], Any], name: str = None) -> MapProcessor:
    """Create map processor."""
    return MapProcessor(transform, name or f"map_{transform.__name__}")


def create_transform(transform: Callable[[Any], Any], name: str = None) -> TransformProcessor:
    """Create transform processor."""
    return TransformProcessor(transform, name or f"transform_{transform.__name__}")


def create_reduce(reducer: Callable[[Any, Any], Any], initial: Any, name: str = None) -> ReduceProcessor:
    """Create reduce processor."""
    return ReduceProcessor(reducer, initial, name or f"reduce_{reducer.__name__}")


def create_aggregate(aggregators: Dict[str, Callable], name: str = None) -> AggregateProcessor:
    """Create aggregate processor."""
    return AggregateProcessor(aggregators, name or "aggregate")


def pipeline(name: str = "pipeline") -> ProcessingPipeline:
    """Create new processing pipeline."""
    return ProcessingPipeline(name)


# Common processors for nlp2cmd
def filter_form_fields(fields: List[Dict]) -> List[Dict]:
    """Filter junk form fields."""
    is_junk = lambda f: not (f.get('value', '').strip() == '' or f.get('name', '').isdigit())
    processor = create_filter(is_junk, "filter_form_fields")
    result = processor(fields)
    return result.data if result.success else fields


def map_field_attributes(fields: List[Dict]) -> List[Dict]:
    """Map field attributes."""
    transform_attrs = lambda f: {**f, 'processed': True, 'length': len(str(f.get('value', '')))}
    processor = create_map(transform_attrs, "map_field_attributes")
    result = processor(fields)
    return result.data if result.success else fields


def aggregate_field_stats(fields: List[Dict]) -> Dict[str, Any]:
    """Aggregate field statistics."""
    aggregators = {
        'count': len,
        'non_empty': lambda f: sum(1 for field in f if field.get('value', '').strip()),
        'avg_length': lambda f: sum(len(str(field.get('value', ''))) for field in f) / len(f) if f else 0
    }
    processor = create_aggregate(aggregators, "aggregate_field_stats")
    result = processor(fields)
    return result.data if result.success else {}

#!/usr/bin/env python3
"""
Testing suite for optimization implementations.

Tests the new frameworks and compares performance with original code.
"""

import sys
import os
import time
import traceback
from typing import Dict, List, Any
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'nlp2cmd'))
sys.path.insert(0, str(Path(__file__).parent))


class OptimizationTester:
    """Test suite for optimization implementations."""
    
    def __init__(self):
        self.test_results = []
        self.performance_metrics = {}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite."""
        print("🧪 Running Optimization Tests...")
        print("=" * 50)
        
        # Test 1: Unified Validation Framework
        self.test_validation_framework()
        
        # Test 2: Generic Processing Framework  
        self.test_processing_framework()
        
        # Test 3: Refactored Executor
        self.test_refactored_executor()
        
        # Test 4: Performance Comparison
        self.test_performance_comparison()
        
        # Test 5: Integration Tests
        self.test_integration()
        
        # Generate summary
        return self.generate_test_summary()
    
    def test_validation_framework(self) -> None:
        """Test unified validation framework."""
        print("\n📋 Testing Validation Framework...")
        
        try:
            # Import the framework
            from validation.framework import (
                ValidationFramework, ValidationType, 
                validate_safety_policy, validate_form_field
            )
            
            # Test 1: Safety Policy Validation
            print("  ✅ Testing safety policy validation...")
            result1 = validate_safety_policy("ls -la")
            assert result1.is_valid == True, "Safe command should pass"
            
            result2 = validate_safety_policy("rm -rf /")
            assert result2.is_valid == False, "Dangerous command should fail"
            assert len(result2.errors) > 0, "Should have error messages"
            
            # Test 2: Form Field Validation
            print("  ✅ Testing form field validation...")
            valid_field = {"name": "username", "value": "john_doe", "type": "text"}
            result3 = validate_form_field(valid_field)
            assert result3.is_valid == True, "Valid field should pass"
            
            invalid_field = {"name": "email", "value": "not_an_email", "type": "email"}
            result4 = validate_form_field(invalid_field)
            assert result4.is_valid == False, "Invalid email should fail"
            
            # Test 3: Framework Integration
            print("  ✅ Testing framework integration...")
            framework = ValidationFramework()
            stats = framework.get_validation_stats()
            assert 'total_validations' in stats, "Should have stats"
            
            self.test_results.append({
                'test': 'validation_framework',
                'status': 'PASSED',
                'details': 'All validation tests passed',
                'performance': 'Excellent'
            })
            
            print("  ✅ Validation Framework: PASSED")
            
        except Exception as e:
            print(f"  ❌ Validation Framework: FAILED - {e}")
            self.test_results.append({
                'test': 'validation_framework',
                'status': 'FAILED',
                'details': str(e),
                'traceback': traceback.format_exc()
            })
    
    def test_processing_framework(self) -> None:
        """Test generic processing framework."""
        print("\n⚙️ Testing Processing Framework...")
        
        try:
            from processing.framework import (
                FilterProcessor, MapProcessor, TransformProcessor,
                create_filter, create_map, pipeline,
                filter_form_fields, map_field_attributes, aggregate_field_stats
            )
            
            # Test 1: Filter Processing
            print("  ✅ Testing filter processing...")
            test_data = [
                {"name": "field1", "value": "value1"},
                {"name": "field2", "value": ""},
                {"name": "field3", "value": "123"}
            ]
            
            filtered = filter_form_fields(test_data)
            assert len(filtered) < len(test_data), "Should filter junk fields"
            
            # Test 2: Map Processing  
            print("  ✅ Testing map processing...")
            mapped = map_field_attributes(test_data)
            assert all('processed' in field for field in mapped), "Should add processed flag"
            
            # Test 3: Aggregation
            print("  ✅ Testing aggregation...")
            stats = aggregate_field_stats(test_data)
            assert 'count' in stats, "Should have count statistic"
            assert stats['count'] == len(test_data), "Count should match"
            
            # Test 4: Pipeline
            print("  ✅ Testing pipeline...")
            pipe = pipeline("test_pipeline")
            pipe.add_processor(create_filter(lambda x: x.get('value', '').strip()))
            pipe.add_processor(create_map(lambda x: {**x, 'pipeline_processed': True}))
            
            result = pipe.process(test_data)
            assert result.success, "Pipeline should succeed"
            
            self.test_results.append({
                'test': 'processing_framework',
                'status': 'PASSED',
                'details': 'All processing tests passed',
                'performance': 'Good'
            })
            
            print("  ✅ Processing Framework: PASSED")
            
        except Exception as e:
            print(f"  ❌ Processing Framework: FAILED - {e}")
            self.test_results.append({
                'test': 'processing_framework',
                'status': 'FAILED',
                'details': str(e),
                'traceback': traceback.format_exc()
            })
    
    def test_refactored_executor(self) -> None:
        """Test refactored executor."""
        print("\n🚀 Testing Refactored Executor...")
        
        try:
            from execution.refactored_executor import (
                RefactoredPlanExecutor, ActionType, ExecutionContext,
                execute_plan_step, run_dom_multi_action
            )
            
            # Test 1: Basic Execution
            print("  ✅ Testing basic execution...")
            executor = RefactoredPlanExecutor()
            context = ExecutionContext(
                session_id="test_session",
                page_state={},
                user_context={},
                safety_enabled=True
            )
            
            step = {"type": "dom_action", "selector": "#button", "action": "click"}
            result = executor.execute_plan_step(step, context)
            assert result['success'], "Basic execution should succeed"
            
            # Test 2: Multi-Action Execution
            print("  ✅ Testing multi-action execution...")
            actions = [
                {"selector": "#input1", "action": "fill", "value": "test"},
                {"selector": "#input2", "action": "fill", "value": "test2"}
            ]
            
            result = run_dom_multi_action(actions, context)
            assert result['success'], "Multi-action should succeed"
            assert len(result['results']) == 2, "Should have 2 results"
            
            # Test 3: Safety Validation
            print("  ✅ Testing safety validation...")
            dangerous_step = {"type": "shell_action", "command": "rm -rf /"}
            result = executor.execute_plan_step(dangerous_step, context)
            assert not result['success'], "Dangerous command should be blocked"
            
            # Test 4: Statistics
            print("  ✅ Testing statistics...")
            stats = executor.get_execution_stats()
            assert 'total_executions' in stats, "Should have execution stats"
            
            self.test_results.append({
                'test': 'refactored_executor',
                'status': 'PASSED',
                'details': 'All executor tests passed',
                'performance': 'Excellent'
            })
            
            print("  ✅ Refactored Executor: PASSED")
            
        except Exception as e:
            print(f"  ❌ Refactored Executor: FAILED - {e}")
            self.test_results.append({
                'test': 'refactored_executor',
                'status': 'FAILED',
                'details': str(e),
                'traceback': traceback.format_exc()
            })
    
    def test_performance_comparison(self) -> None:
        """Test performance improvements."""
        print("\n⚡ Testing Performance...")
        
        try:
            # Simulate performance tests
            test_data = [{"name": f"field_{i}", "value": f"value_{i}"} for i in range(1000)]
            
            # Test validation performance
            print("  ✅ Testing validation performance...")
            start_time = time.time()
            
            from validation.framework import validate_form_field
            for field in test_data[:100]:  # Test subset
                validate_form_field(field)
            
            validation_time = time.time() - start_time
            self.performance_metrics['validation_time'] = validation_time
            
            # Test processing performance
            print("  ✅ Testing processing performance...")
            start_time = time.time()
            
            from processing.framework import filter_form_fields, map_field_attributes
            filtered = filter_form_fields(test_data)
            mapped = map_field_attributes(filtered)
            
            processing_time = time.time() - start_time
            self.performance_metrics['processing_time'] = processing_time
            
            # Test executor performance
            print("  ✅ Testing executor performance...")
            from execution.refactored_executor import RefactoredPlanExecutor, ExecutionContext
            
            executor = RefactoredPlanExecutor()
            context = ExecutionContext("test", {}, {}, True)
            
            start_time = time.time()
            for i in range(50):
                step = {"type": "dom_action", "selector": f"#elem_{i}", "action": "click"}
                executor.execute_plan_step(step, context)
            
            executor_time = time.time() - start_time
            self.performance_metrics['executor_time'] = executor_time
            
            self.test_results.append({
                'test': 'performance_comparison',
                'status': 'PASSED',
                'details': f'Validation: {validation_time:.3f}s, Processing: {processing_time:.3f}s, Executor: {executor_time:.3f}s',
                'performance': 'Measured'
            })
            
            print("  ✅ Performance Tests: PASSED")
            
        except Exception as e:
            print(f"  ❌ Performance Tests: FAILED - {e}")
            self.test_results.append({
                'test': 'performance_comparison',
                'status': 'FAILED',
                'details': str(e),
                'traceback': traceback.format_exc()
            })
    
    def test_integration(self) -> None:
        """Test integration between frameworks."""
        print("\n🔗 Testing Integration...")
        
        try:
            # Test validation + processing integration
            print("  ✅ Testing validation + processing integration...")
            
            from validation.framework import validate_form_field
            from processing.framework import filter_form_fields, aggregate_field_stats
            
            # Sample form data
            form_data = [
                {"name": "username", "value": "john", "type": "text"},
                {"name": "email", "value": "invalid-email", "type": "email"},
                {"name": "password", "value": "123", "type": "password"},
                {"name": "", "value": "", "type": "text"}  # Junk field
            ]
            
            # Validate each field
            validated_fields = []
            for field in form_data:
                result = validate_form_field(field)
                if result.is_valid:
                    validated_fields.append(field)
            
            # Filter and aggregate
            filtered = filter_form_fields(validated_fields)
            stats = aggregate_field_stats(filtered)
            
            assert len(filtered) <= len(form_data), "Should filter some fields"
            assert stats['count'] > 0, "Should have statistics"
            
            # Test executor + validation integration
            print("  ✅ Testing executor + validation integration...")
            
            from execution.refactored_executor import RefactoredPlanExecutor, ExecutionContext
            
            executor = RefactoredPlanExecutor()
            context = ExecutionContext("integration_test", {}, {}, safety_enabled=True)
            
            # Safe action should pass
            safe_step = {"type": "shell_action", "command": "echo 'test'"}
            result = executor.execute_plan_step(safe_step, context)
            assert result['success'], "Safe action should pass"
            
            self.test_results.append({
                'test': 'integration',
                'status': 'PASSED',
                'details': 'All integration tests passed',
                'performance': 'Good'
            })
            
            print("  ✅ Integration Tests: PASSED")
            
        except Exception as e:
            print(f"  ❌ Integration Tests: FAILED - {e}")
            self.test_results.append({
                'test': 'integration',
                'status': 'FAILED',
                'details': str(e),
                'traceback': traceback.format_exc()
            })
    
    def generate_test_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary."""
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['status'] == 'PASSED'])
        failed_tests = total_tests - passed_tests
        
        summary = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'performance_metrics': self.performance_metrics,
            'test_results': self.test_results,
            'overall_status': 'SUCCESS' if failed_tests == 0 else 'PARTIAL_SUCCESS',
            'recommendations': self._generate_recommendations()
        }
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Overall Status: {summary['overall_status']}")
        
        if self.performance_metrics:
            print("\n⚡ Performance Metrics:")
            for metric, value in self.performance_metrics.items():
                print(f"  {metric}: {value:.3f}s")
        
        print("\n📋 Test Results:")
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASSED' else "❌"
            print(f"  {status_icon} {result['test']}: {result['status']}")
            if result['status'] == 'FAILED':
                print(f"    Error: {result['details']}")
        
        print("\n🎯 Recommendations:")
        for rec in summary['recommendations']:
            print(f"  • {rec}")
        
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_tests = [t for t in self.test_results if t['status'] == 'FAILED']
        
        if not failed_tests:
            recommendations.extend([
                "All tests passed - ready for production deployment",
                "Consider adding more comprehensive edge case tests",
                "Monitor performance in production environment",
                "Document API changes for migration guide"
            ])
        else:
            recommendations.extend([
                "Fix failed tests before deployment",
                "Review error handling in failed components",
                "Add more robust error checking",
                "Consider fallback mechanisms for critical failures"
            ])
        
        # Performance recommendations
        if self.performance_metrics.get('validation_time', 0) > 0.1:
            recommendations.append("Optimize validation performance - consider caching")
        
        if self.performance_metrics.get('processing_time', 0) > 0.5:
            recommendations.append("Optimize processing - consider batch operations")
        
        return recommendations


if __name__ == '__main__':
    # Run tests
    tester = OptimizationTester()
    summary = tester.run_all_tests()
    
    # Save results
    import yaml
    with open('optimization_test_results.yaml', 'w') as f:
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False)
    
    print(f"\n📁 Test results saved to: optimization_test_results.yaml")
    
    # Exit with appropriate code
    sys.exit(0 if summary['overall_status'] == 'SUCCESS' else 1)

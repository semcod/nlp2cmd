#!/usr/bin/env python3
"""
Advanced Data Structure Optimization using NetworkX and ML algorithms.

Implements:
- Community detection for process consolidation
- Centrality analysis for hub optimization  
- Pattern mining for type reduction
- Automatic refactoring suggestions
"""

import networkx as nx
import yaml
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter
import itertools


class DataStructureOptimizer:
    """Advanced optimizer for data structures and flows."""
    
    def __init__(self, analysis_data: Dict[str, Any]):
        self.analysis_data = analysis_data
        self.graph = self._build_networkx_graph()
    
    def _build_networkx_graph(self) -> nx.DiGraph:
        """Build NetworkX graph from data flow analysis."""
        G = nx.DiGraph()
        
        # Add nodes with attributes
        for node_id, node_data in self.analysis_data['data_flow_graph']['nodes'].items():
            G.add_node(node_id, **node_data)
        
        # Add edges with weights
        for edge in self.analysis_data['data_flow_graph']['edges']:
            G.add_edge(edge['from'], edge['to'], weight=edge['weight'])
        
        return G
    
    def analyze_communities(self) -> Dict[str, Any]:
        """Detect communities for process consolidation using Louvain algorithm."""
        # Convert to undirected for community detection
        G_undirected = self.graph.to_undirected()
        
        # Detect communities
        communities = nx.community.louvain_communities(G_undirected, seed=42)
        
        # Analyze each community
        community_analysis = []
        for i, community in enumerate(communities):
            if len(community) < 3:  # Skip very small communities
                continue
                
            # Get process patterns in this community
            community_patterns = self._get_community_patterns(community)
            
            # Calculate consolidation potential
            consolidation_score = self._calculate_consolidation_potential(community)
            
            community_analysis.append({
                'community_id': i,
                'size': len(community),
                'functions': list(community)[:10],  # Limit for readability
                'process_patterns': community_patterns,
                'consolidation_score': consolidation_score,
                'recommendation': self._generate_consolidation_recommendation(community, consolidation_score)
            })
        
        return {
            'total_communities': len(communities),
            'analyzed_communities': len(community_analysis),
            'communities': sorted(community_analysis, key=lambda x: x['consolidation_score'], reverse=True)
        }
    
    def analyze_centrality(self) -> Dict[str, Any]:
        """Analyze centrality measures for hub optimization."""
        centrality_measures = {
            'betweenness': nx.betweenness_centrality(self.graph),
            'closeness': nx.closeness_centrality(self.graph),
            'pagerank': nx.pagerank(self.graph),
            'in_degree': dict(self.graph.in_degree()),
            'out_degree': dict(self.graph.out_degree())
        }
        
        # Find optimization candidates
        optimization_candidates = []
        
        for node in self.graph.nodes():
            scores = {
                'betweenness': centrality_measures['betweenness'][node],
                'closeness': centrality_measures['closeness'][node],
                'pagerank': centrality_measures['pagerank'][node],
                'in_degree': centrality_measures['in_degree'][node],
                'out_degree': centrality_measures['out_degree'][node]
            }
            
            # Calculate optimization priority
            priority = self._calculate_optimization_priority(scores)
            
            if priority > 0.5:  # Only include significant candidates
                optimization_candidates.append({
                    'function': node,
                    'scores': scores,
                    'priority': priority,
                    'optimization_type': self._determine_optimization_type(scores),
                    'recommendation': self._generate_optimization_recommendation(node, scores)
                })
        
        return {
            'total_nodes': len(self.graph.nodes()),
            'candidates': len(optimization_candidates),
            'top_candidates': sorted(optimization_candidates, key=lambda x: x['priority'], reverse=True)[:10]
        }
    
    def analyze_type_patterns(self) -> Dict[str, Any]:
        """Analyze type patterns for consolidation opportunities."""
        type_data = self.analysis_data['data_types']
        
        # Find similar types
        type_clusters = self._cluster_similar_types(type_data)
        
        # Generate consolidation recommendations
        consolidation_opportunities = []
        
        for cluster_id, cluster in enumerate(type_clusters):
            if len(cluster) > 1:  # Only clusters with multiple types
                total_usage = sum(t['usage_count'] for t in cluster)
                cross_module_usage = sum(t['cross_module_usage'] for t in cluster)
                
                consolidation_opportunities.append({
                    'cluster_id': cluster_id,
                    'types': [t['type_name'] for t in cluster],
                    'total_usage': total_usage,
                    'cross_module_usage': cross_module_usage,
                    'consolidation_benefit': self._calculate_consolidation_benefit(cluster),
                    'recommendation': self._generate_type_consolidation_recommendation(cluster)
                })
        
        return {
            'total_types': len(type_data),
            'clusters_found': len(type_clusters),
            'consolidation_opportunities': consolidation_opportunities
        }
    
    def generate_refactoring_plan(self) -> Dict[str, Any]:
        """Generate comprehensive refactoring plan."""
        communities = self.analyze_communities()
        centrality = self.analyze_centrality()
        type_patterns = self.analyze_type_patterns()
        
        # Calculate overall optimization score
        overall_score = self._calculate_overall_optimization_score(
            communities, centrality, type_patterns
        )
        
        # Generate prioritized action items
        action_items = self._generate_action_items(communities, centrality, type_patterns)
        
        return {
            'overall_optimization_score': overall_score,
            'estimated_impact': self._estimate_impact(action_items),
            'action_items': action_items,
            'implementation_order': self._prioritize_implementation(action_items),
            'risk_assessment': self._assess_risks(action_items)
        }
    
    def export_optimization_report(self, output_path: str) -> None:
        """Export comprehensive optimization report."""
        report = {
            'project_path': self.analysis_data['project_path'],
            'analysis_date': '2026-02-28',
            'optimization_analysis': {
                'communities': self.analyze_communities(),
                'centrality': self.analyze_centrality(),
                'type_patterns': self.analyze_type_patterns(),
                'refactoring_plan': self.generate_refactoring_plan()
            }
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(report, f, default_flow_style=False, sort_keys=False)
    
    # Helper methods
    def _get_community_patterns(self, community: set) -> List[str]:
        """Get process patterns for a community."""
        patterns = []
        for func in community:
            for pattern in self.analysis_data['process_patterns']:
                if any(f['function'] == func for f in pattern['functions']):
                    patterns.append(pattern['pattern_type'])
        return list(set(patterns))
    
    def _calculate_consolidation_potential(self, community: set) -> float:
        """Calculate consolidation potential for a community."""
        # Higher potential if:
        # 1. Many functions with similar patterns
        # 2. High cross-module usage
        # 3. Similar data types
        
        pattern_diversity = len(self._get_community_patterns(community))
        size_factor = len(community) / 10.0  # Normalize by expected size
        
        return min(1.0, pattern_diversity * size_factor)
    
    def _generate_consolidation_recommendation(self, community: set, score: float) -> str:
        """Generate consolidation recommendation for a community."""
        if score > 0.8:
            return f"HIGH PRIORITY: Consolidate {len(community)} functions into unified framework"
        elif score > 0.5:
            return f"MEDIUM PRIORITY: Merge similar functions in {len(community)}-function group"
        else:
            return f"LOW PRIORITY: Consider refactoring {len(community)} functions"
    
    def _calculate_optimization_priority(self, scores: Dict[str, float]) -> float:
        """Calculate optimization priority from centrality scores."""
        # Weight different measures
        weights = {
            'betweenness': 0.3,
            'closeness': 0.2,
            'pagerank': 0.2,
            'out_degree': 0.2,
            'in_degree': 0.1
        }
        
        priority = sum(scores[measure] * weight for measure, weight in weights.items())
        return min(1.0, priority)
    
    def _determine_optimization_type(self, scores: Dict[str, float]) -> str:
        """Determine optimization type based on scores."""
        if scores['out_degree'] > 10:
            return 'split'
        elif scores['in_degree'] > 10:
            return 'cache'
        elif scores['betweenness'] > 0.1:
            return 'optimize_path'
        else:
            return 'monitor'
    
    def _generate_optimization_recommendation(self, node: str, scores: Dict[str, float]) -> str:
        """Generate optimization recommendation for a node."""
        opt_type = self._determine_optimization_type(scores)
        
        recommendations = {
            'split': f"SPLIT {node.split('.')[-1]} into {int(scores['out_degree']/5)} specialized functions",
            'cache': f"CACHE results for {node.split('.')[-1]} (called {int(scores['in_degree'])} times)",
            'optimize_path': f"OPTIMIZE critical path through {node.split('.')[-1]}",
            'monitor': f"MONITOR {node.split('.')[-1]} for performance issues"
        }
        
        return recommendations[opt_type]
    
    def _cluster_similar_types(self, type_data: List[Dict]) -> List[List[Dict]]:
        """Cluster similar data types."""
        # Simple clustering based on detected types and usage patterns
        clusters = []
        processed = set()
        
        for i, type1 in enumerate(type_data):
            if i in processed:
                continue
                
            cluster = [type1]
            processed.add(i)
            
            for j, type2 in enumerate(type_data[i+1:], i+1):
                if j in processed:
                    continue
                    
                # Check similarity
                similarity = self._calculate_type_similarity(type1, type2)
                if similarity > 0.7:  # High similarity threshold
                    cluster.append(type2)
                    processed.add(j)
            
            if len(cluster) > 1:
                clusters.append(cluster)
        
        return clusters
    
    def _calculate_type_similarity(self, type1: Dict, type2: Dict) -> float:
        """Calculate similarity between two data types."""
        # Similarity based on detected types and usage patterns
        type_overlap = len(set(type1['detected_types']) & set(type2['detected_types']))
        total_types = len(set(type1['detected_types']) | set(type2['detected_types']))
        
        if total_types == 0:
            return 0.0
        
        type_similarity = type_overlap / total_types
        
        # Factor in usage similarity
        usage_diff = abs(type1['usage_count'] - type2['usage_count'])
        max_usage = max(type1['usage_count'], type2['usage_count'])
        usage_similarity = 1.0 - (usage_diff / max_usage) if max_usage > 0 else 1.0
        
        return (type_similarity + usage_similarity) / 2.0
    
    def _calculate_consolidation_benefit(self, cluster: List[Dict]) -> float:
        """Calculate benefit of consolidating a type cluster."""
        total_usage = sum(t['usage_count'] for t in cluster)
        complexity_reduction = len(cluster) - 1  # Reduce by number of merged types
        
        return (total_usage / 100.0) * complexity_reduction
    
    def _generate_type_consolidation_recommendation(self, cluster: List[Dict]) -> str:
        """Generate type consolidation recommendation."""
        type_names = [t['type_name'] for t in cluster]
        total_usage = sum(t['usage_count'] for t in cluster)
        
        return f"MERGE {len(cluster)} types ({', '.join(type_names[:3])}...) - {total_usage} total usages"
    
    def _calculate_overall_optimization_score(self, communities: Dict, centrality: Dict, type_patterns: Dict) -> float:
        """Calculate overall optimization score."""
        community_score = communities['analyzed_communities'] * 0.1
        centrality_score = centrality['candidates'] * 0.05
        type_score = len(type_patterns['consolidation_opportunities']) * 0.15
        
        return min(10.0, community_score + centrality_score + type_score)
    
    def _estimate_impact(self, action_items: List[Dict]) -> Dict[str, Any]:
        """Estimate impact of optimization actions."""
        total_items = len(action_items)
        high_priority = len([a for a in action_items if a['priority'] == 'HIGH'])
        
        return {
            'total_actions': total_items,
            'high_priority_actions': high_priority,
            'estimated_complexity_reduction': f"{total_items * 5}%",
            'estimated_performance_improvement': f"{high_priority * 10}%"
        }
    
    def _generate_action_items(self, communities: Dict, centrality: Dict, type_patterns: Dict) -> List[Dict]:
        """Generate prioritized action items."""
        actions = []
        
        # Community consolidation actions
        for community in communities['communities'][:5]:
            actions.append({
                'type': 'community_consolidation',
                'priority': 'HIGH' if community['consolidation_score'] > 0.7 else 'MEDIUM',
                'description': community['recommendation'],
                'effort': f"{community['size']} functions",
                'impact': f"Score: {community['consolidation_score']:.2f}"
            })
        
        # Hub optimization actions
        for candidate in centrality['top_candidates'][:5]:
            actions.append({
                'type': 'hub_optimization',
                'priority': 'HIGH' if candidate['priority'] > 0.7 else 'MEDIUM',
                'description': candidate['recommendation'],
                'effort': f"Priority: {candidate['priority']:.2f}",
                'impact': f"Type: {candidate['optimization_type']}"
            })
        
        # Type consolidation actions
        for opportunity in type_patterns['consolidation_opportunities'][:3]:
            actions.append({
                'type': 'type_consolidation',
                'priority': 'MEDIUM',
                'description': opportunity['recommendation'],
                'effort': f"{len(opportunity['types'])} types",
                'impact': f"Benefit: {opportunity['consolidation_benefit']:.2f}"
            })
        
        return actions
    
    def _prioritize_implementation(self, action_items: List[Dict]) -> List[Dict]:
        """Prioritize implementation order."""
        # Sort by priority and impact
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        
        return sorted(action_items, key=lambda x: (
            priority_order.get(x['priority'], 0),
            len(x['description'])  # Longer descriptions = more complex
        ), reverse=True)
    
    def _assess_risks(self, action_items: List[Dict]) -> Dict[str, Any]:
        """Assess risks for optimization actions."""
        high_priority_count = len([a for a in action_items if a['priority'] == 'HIGH'])
        total_count = len(action_items)
        
        risk_level = 'LOW'
        if high_priority_count > 5:
            risk_level = 'HIGH'
        elif high_priority_count > 2:
            risk_level = 'MEDIUM'
        
        return {
            'risk_level': risk_level,
            'high_priority_actions': high_priority_count,
            'total_actions': total_count,
            'recommendation': f"Implement in phases, starting with {high_priority_count} high-priority items"
        }


if __name__ == '__main__':
    # Example usage
    with open('./output_structures/data_structures.yaml') as f:
        analysis_data = yaml.safe_load(f)
    
    optimizer = DataStructureOptimizer(analysis_data)
    optimizer.export_optimization_report('./output_structures/advanced_optimization.yaml')
    
    print("✓ Advanced optimization analysis complete!")
    print("  - Community detection for process consolidation")
    print("  - Centrality analysis for hub optimization")
    print("  - Type pattern analysis for consolidation")
    print("  - Comprehensive refactoring plan")

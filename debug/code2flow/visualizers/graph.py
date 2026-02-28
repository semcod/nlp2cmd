"""Graph visualization using NetworkX and matplotlib."""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx
from typing import Dict
from pathlib import Path

from ..core.models import AnalysisResult
from ..core.config import NODE_COLORS


class GraphVisualizer:
    """Visualize analysis results as graphs."""
    
    def __init__(self, result: AnalysisResult):
        self.result = result
        self.graph = nx.DiGraph()
        self._build_graph()
        
    def _build_graph(self):
        """Build NetworkX graph from analysis result."""
        # Add nodes
        for node_id, node in self.result.nodes.items():
            color = NODE_COLORS.get(node.type, '#757575')
            self.graph.add_node(
                node_id,
                label=node.label[:30],
                type=node.type,
                color=color,
                function=node.function
            )
            
        # Add edges
        for edge in self.result.edges:
            self.graph.add_edge(
                edge.source,
                edge.target,
                edge_type=edge.edge_type,
                conditions=edge.conditions
            )
            
    def visualize_cfg(self, filepath: str, layout: str = 'spring'):
        """Create control flow visualization."""
        plt.figure(figsize=(16, 12))
        
        # Choose layout
        if layout == 'spring':
            pos = nx.spring_layout(self.graph, k=2, iterations=50, seed=42)
        elif layout == 'hierarchical':
            pos = self._hierarchical_layout()
        elif layout == 'kamada':
            pos = nx.kamada_kawai_layout(self.graph)
        else:
            pos = nx.shell_layout(self.graph)
            
        # Get node colors
        node_colors = []
        for node_id in self.graph.nodes():
            node_type = self.graph.nodes[node_id].get('type', 'DEFAULT')
            node_colors.append(NODE_COLORS.get(node_type, '#757575'))
            
        # Draw graph
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_color=node_colors,
            node_size=600,
            alpha=0.8,
            edgecolors='white',
            linewidths=2
        )
        
        nx.draw_networkx_edges(
            self.graph, pos,
            alpha=0.4,
            arrows=True,
            arrowsize=15,
            arrowstyle='->',
            edge_color='#666666',
            width=1.5
        )
        
        # Draw labels for important nodes
        labels = {}
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            if node_data.get('type') in ['FUNC', 'IF', 'CALL']:
                label = node_data.get('label', '') or ''
                labels[node_id] = label[:25]
                
        nx.draw_networkx_labels(
            self.graph, pos, labels,
            font_size=8,
            font_color='white',
            font_weight='bold'
        )
        
        # Add legend
        legend_elements = [
            patches.Patch(color=NODE_COLORS['FUNC'], label='Function'),
            patches.Patch(color=NODE_COLORS['CALL'], label='Call'),
            patches.Patch(color=NODE_COLORS['IF'], label='Decision'),
            patches.Patch(color=NODE_COLORS['FOR'], label='Loop'),
            patches.Patch(color=NODE_COLORS['RETURN'], label='Return')
        ]
        plt.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        plt.title('Control Flow Graph', fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
    def visualize_call_graph(self, filepath: str):
        """Visualize call graph."""
        # Build call graph
        call_graph = nx.DiGraph()
        
        for func_name, func_info in self.result.functions.items():
            short_name = func_name.split('.')[-1]
            call_graph.add_node(func_name, label=short_name)
            
            for callee in func_info.calls:
                call_graph.add_edge(func_name, callee)
                
        if len(call_graph.nodes()) == 0:
            return  # Nothing to visualize
            
        plt.figure(figsize=(14, 10))
        
        # Layout
        pos = nx.spring_layout(call_graph, k=1.5, iterations=50, seed=42)
        
        # Node sizes based on calls
        node_sizes = []
        for node in call_graph.nodes():
            out_degree = call_graph.out_degree(node)
            in_degree = call_graph.in_degree(node)
            size = 300 + (out_degree + in_degree) * 150
            node_sizes.append(size)
            
        # Draw
        nx.draw_networkx_nodes(
            call_graph, pos,
            node_color='#4CAF50',
            node_size=node_sizes,
            alpha=0.8,
            edgecolors='white',
            linewidths=2
        )
        
        nx.draw_networkx_edges(
            call_graph, pos,
            alpha=0.5,
            arrows=True,
            arrowsize=20,
            edge_color='#2196F3',
            width=2
        )
        
        # Labels
        labels = {n: (call_graph.nodes[n].get('label') or n)[:20] for n in call_graph.nodes()}
        nx.draw_networkx_labels(
            call_graph, pos, labels,
            font_size=9,
            font_weight='bold'
        )
        
        plt.title('Function Call Graph', fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
    def _hierarchical_layout(self) -> Dict:
        """Create hierarchical layout grouped by function."""
        from collections import defaultdict
        
        # Group nodes by function
        function_groups = defaultdict(list)
        for node_id, node in self.result.nodes.items():
            func = node.function or '__global__'
            function_groups[func].append(node_id)
            
        # Position nodes
        pos = {}
        y_offset = 0
        
        for func_name, nodes in sorted(function_groups.items()):
            for i, node_id in enumerate(nodes):
                x = i * 2
                y = -y_offset
                pos[node_id] = (x, y)
            y_offset += 3
            
        return pos

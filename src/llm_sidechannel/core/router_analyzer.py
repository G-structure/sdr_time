"""Router analysis utilities for Mixture of Experts models."""

import torch
import numpy as np
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter


class RouterAnalyzer:
    """Analyzer for MoE router decisions and expert utilization."""
    
    def __init__(self, num_experts: int = 8, experts_per_token: int = 2):
        """
        Initialize router analyzer.
        
        Args:
            num_experts: Total number of experts in the model
            experts_per_token: Number of experts selected per token
        """
        self.num_experts = num_experts
        self.experts_per_token = experts_per_token
        self.tokenizer = None
    
    def set_tokenizer(self, tokenizer):
        """Set tokenizer for token-level analysis."""
        self.tokenizer = tokenizer
    
    def analyze_routing_decisions(
        self,
        routing_decisions: List[Dict[str, Any]],
        tokens: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Analyze router decisions across all layers and tokens.
        
        Args:
            routing_decisions: List of routing decisions from MixtralClient
            tokens: Optional token IDs for detailed analysis
            
        Returns:
            Comprehensive analysis results
        """
        # Group decisions by layer
        layer_decisions = defaultdict(list)
        for decision in routing_decisions:
            layer_decisions[decision['layer']].append(decision)
        
        # Global analysis
        global_expert_usage = Counter()
        total_decisions = len(routing_decisions)
        
        for decision in routing_decisions:
            for expert_id in decision['selected_experts']:
                global_expert_usage[expert_id] += 1
        
        # Calculate global statistics
        global_stats = {
            'total_routing_decisions': total_decisions,
            'global_expert_usage': dict(global_expert_usage),
            'global_expert_percentages': {
                expert_id: (count / total_decisions) * 100 
                for expert_id, count in global_expert_usage.items()
            } if total_decisions > 0 else {},
            'most_used_expert': global_expert_usage.most_common(1)[0] if global_expert_usage else (None, 0),
            'least_used_expert': global_expert_usage.most_common()[-1] if global_expert_usage else (None, 0),
            'unused_experts': [i for i in range(self.num_experts) if i not in global_expert_usage],
        }
        
        return {
            'layer_decisions': dict(layer_decisions),
            'global_statistics': global_stats,
            'summary': self._generate_summary(global_stats)
        }
    
    def _generate_summary(self, global_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the analysis."""
        total_decisions = global_stats['total_routing_decisions']
        global_usage = global_stats['global_expert_usage']
        usage_values = list(global_usage.values()) if global_usage else [0]
        
        return {
            'total_routing_decisions': total_decisions,
            'num_experts_used': len(global_usage),
            'num_experts_unused': len(global_stats['unused_experts']),
            'expert_usage_distribution': {
                'mean': np.mean(usage_values) if usage_values else 0,
                'std': np.std(usage_values) if usage_values else 0,
                'min': np.min(usage_values) if usage_values else 0,
                'max': np.max(usage_values) if usage_values else 0
            } if usage_values else {}
        }
    
    def get_expert_usage_summary(self, analysis_results: Dict[str, Any]) -> str:
        """Get a human-readable summary of expert usage."""
        global_stats = analysis_results['global_statistics']
        summary = analysis_results['summary']
        
        report = []
        report.append("=== Expert Usage Analysis ===")
        report.append(f"Total routing decisions: {summary['total_routing_decisions']}")
        report.append(f"Experts used: {summary['num_experts_used']}/{self.num_experts}")
        report.append(f"Unused experts: {summary['num_experts_unused']}")
        
        if global_stats['most_used_expert'][0] is not None:
            expert_id, count = global_stats['most_used_expert']
            percentage = global_stats['global_expert_percentages'].get(expert_id, 0)
            report.append(f"Most used expert: #{expert_id} ({count} times, {percentage:.1f}%)")
        
        if global_stats['unused_experts']:
            report.append(f"Unused experts: {global_stats['unused_experts']}")
        
        return "\n".join(report) 
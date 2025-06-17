"""Expert usage analysis for MoE models."""

from typing import Dict, List, Any, Optional
import numpy as np
from collections import Counter, defaultdict


class ExpertUsageAnalyzer:
    """Analyzer for expert usage patterns in Mixture of Experts models."""
    
    def __init__(self, num_experts: int = 8):
        """
        Initialize expert usage analyzer.
        
        Args:
            num_experts: Total number of experts in the model
        """
        self.num_experts = num_experts
        self.usage_history = []
    
    def analyze_expert_distribution(
        self, 
        expert_usage: Dict[int, int]
    ) -> Dict[str, Any]:
        """
        Analyze the distribution of expert usage.
        
        Args:
            expert_usage: Dictionary mapping expert IDs to usage counts
            
        Returns:
            Analysis of expert usage distribution
        """
        total_usage = sum(expert_usage.values()) if expert_usage else 0
        
        if total_usage == 0:
            return {
                'total_usage': 0,
                'entropy': 0.0,
                'gini_coefficient': 0.0,
                'load_balance_score': 0.0,
                'expert_percentages': {},
                'analysis': 'No expert usage data'
            }
        
        # Calculate percentages
        expert_percentages = {
            expert_id: (count / total_usage) * 100
            for expert_id, count in expert_usage.items()
        }
        
        # Fill in zeros for unused experts
        all_expert_usage = [expert_usage.get(i, 0) for i in range(self.num_experts)]
        all_expert_percentages = [(count / total_usage) * 100 for count in all_expert_usage]
        
        # Calculate entropy (higher = more uniform distribution)
        entropy = self._calculate_entropy(all_expert_percentages)
        
        # Calculate Gini coefficient (lower = more equal distribution)
        gini = self._calculate_gini_coefficient(all_expert_usage)
        
        # Calculate load balance score (higher = better balance)
        load_balance = self._calculate_load_balance_score(all_expert_usage)
        
        return {
            'total_usage': total_usage,
            'entropy': entropy,
            'gini_coefficient': gini,
            'load_balance_score': load_balance,
            'expert_percentages': expert_percentages,
            'unused_experts': [i for i in range(self.num_experts) if all_expert_usage[i] == 0],
            'most_used_expert': max(expert_usage.items(), key=lambda x: x[1]) if expert_usage else (None, 0),
            'least_used_expert': min(expert_usage.items(), key=lambda x: x[1]) if expert_usage else (None, 0),
            'analysis': self._interpret_distribution(entropy, gini, load_balance)
        }
    
    def compare_usage_patterns(
        self,
        usage_patterns: List[Dict[int, int]],
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare usage patterns across multiple scenarios.
        
        Args:
            usage_patterns: List of expert usage dictionaries
            labels: Optional labels for each pattern
            
        Returns:
            Comparison analysis
        """
        if not usage_patterns:
            return {'error': 'No usage patterns provided'}
        
        if labels is None:
            labels = [f"Pattern {i+1}" for i in range(len(usage_patterns))]
        
        analyses = []
        for pattern in usage_patterns:
            analyses.append(self.analyze_expert_distribution(pattern))
        
        # Compare metrics across patterns
        entropies = [analysis['entropy'] for analysis in analyses]
        ginis = [analysis['gini_coefficient'] for analysis in analyses]
        load_balances = [analysis['load_balance_score'] for analysis in analyses]
        
        # Calculate correlations between usage patterns
        correlations = []
        for i in range(len(usage_patterns)):
            for j in range(i + 1, len(usage_patterns)):
                usage_i = [usage_patterns[i].get(k, 0) for k in range(self.num_experts)]
                usage_j = [usage_patterns[j].get(k, 0) for k in range(self.num_experts)]
                
                if sum(usage_i) > 0 and sum(usage_j) > 0:
                    corr = np.corrcoef(usage_i, usage_j)[0, 1]
                    correlations.append({
                        'patterns': (labels[i], labels[j]),
                        'correlation': corr
                    })
        
        return {
            'individual_analyses': dict(zip(labels, analyses)),
            'comparisons': {
                'entropy_range': (min(entropies), max(entropies)),
                'gini_range': (min(ginis), max(ginis)),
                'load_balance_range': (min(load_balances), max(load_balances)),
                'most_balanced': labels[np.argmax(load_balances)],
                'least_balanced': labels[np.argmin(load_balances)],
                'correlations': correlations,
                'avg_correlation': np.mean([c['correlation'] for c in correlations]) if correlations else 0.0
            }
        }
    
    def track_usage_over_time(
        self,
        expert_usage: Dict[int, int],
        timestamp: Optional[str] = None
    ):
        """
        Track expert usage over time.
        
        Args:
            expert_usage: Current expert usage
            timestamp: Optional timestamp for this measurement
        """
        analysis = self.analyze_expert_distribution(expert_usage)
        
        entry = {
            'timestamp': timestamp or len(self.usage_history),
            'usage': expert_usage,
            'analysis': analysis
        }
        
        self.usage_history.append(entry)
    
    def get_usage_trends(self) -> Dict[str, Any]:
        """
        Analyze trends in expert usage over time.
        
        Returns:
            Trend analysis of expert usage
        """
        if len(self.usage_history) < 2:
            return {'error': 'Insufficient history for trend analysis'}
        
        # Extract time series data
        entropies = [entry['analysis']['entropy'] for entry in self.usage_history]
        ginis = [entry['analysis']['gini_coefficient'] for entry in self.usage_history]
        load_balances = [entry['analysis']['load_balance_score'] for entry in self.usage_history]
        
        # Calculate trends (simple linear regression slope)
        def calculate_trend(values):
            n = len(values)
            x = np.arange(n)
            slope = np.polyfit(x, values, 1)[0]
            return slope
        
        return {
            'history_length': len(self.usage_history),
            'trends': {
                'entropy': calculate_trend(entropies),
                'gini_coefficient': calculate_trend(ginis),
                'load_balance_score': calculate_trend(load_balances)
            },
            'current_vs_start': {
                'entropy_change': entropies[-1] - entropies[0],
                'gini_change': ginis[-1] - ginis[0],
                'load_balance_change': load_balances[-1] - load_balances[0]
            },
            'interpretation': self._interpret_trends(
                calculate_trend(entropies),
                calculate_trend(ginis),
                calculate_trend(load_balances)
            )
        }
    
    def _calculate_entropy(self, percentages: List[float]) -> float:
        """Calculate Shannon entropy of expert usage distribution."""
        # Convert percentages to probabilities
        probs = [p / 100.0 for p in percentages if p > 0]
        if not probs:
            return 0.0
        
        entropy = -sum(p * np.log2(p) for p in probs)
        return entropy
    
    def _calculate_gini_coefficient(self, usage_counts: List[int]) -> float:
        """Calculate Gini coefficient of expert usage distribution."""
        if not usage_counts or sum(usage_counts) == 0:
            return 0.0
        
        sorted_counts = sorted(usage_counts)
        n = len(sorted_counts)
        cumsum = np.cumsum(sorted_counts)
        
        gini = (n + 1 - 2 * sum((n + 1 - i) * count for i, count in enumerate(sorted_counts, 1))) / (n * sum(sorted_counts))
        return gini
    
    def _calculate_load_balance_score(self, usage_counts: List[int]) -> float:
        """Calculate load balance score (1.0 = perfectly balanced, 0.0 = completely unbalanced)."""
        if not usage_counts or sum(usage_counts) == 0:
            return 0.0
        
        mean_usage = np.mean(usage_counts)
        if mean_usage == 0:
            return 0.0
        
        # Coefficient of variation (lower is better balanced)
        cv = np.std(usage_counts) / mean_usage
        
        # Convert to score where 1.0 is perfect balance
        # Use exponential decay to map CV to [0, 1]
        score = np.exp(-cv)
        return score
    
    def _interpret_distribution(self, entropy: float, gini: float, load_balance: float) -> str:
        """Interpret the distribution metrics."""
        interpretations = []
        
        if entropy > 2.5:
            interpretations.append("High entropy - experts are used fairly uniformly")
        elif entropy < 1.0:
            interpretations.append("Low entropy - usage is concentrated in few experts")
        else:
            interpretations.append("Moderate entropy - mixed usage pattern")
        
        if gini < 0.2:
            interpretations.append("Low Gini - relatively equal distribution")
        elif gini > 0.6:
            interpretations.append("High Gini - highly unequal distribution")
        else:
            interpretations.append("Moderate Gini - some inequality in usage")
        
        if load_balance > 0.8:
            interpretations.append("Good load balance")
        elif load_balance < 0.4:
            interpretations.append("Poor load balance")
        else:
            interpretations.append("Moderate load balance")
        
        return "; ".join(interpretations)
    
    def _interpret_trends(self, entropy_trend: float, gini_trend: float, balance_trend: float) -> str:
        """Interpret trends over time."""
        trends = []
        
        if abs(entropy_trend) > 0.01:
            direction = "increasing" if entropy_trend > 0 else "decreasing"
            trends.append(f"Entropy {direction}")
        
        if abs(gini_trend) > 0.01:
            direction = "increasing" if gini_trend > 0 else "decreasing"
            impact = "more unequal" if gini_trend > 0 else "more equal"
            trends.append(f"Distribution becoming {impact}")
        
        if abs(balance_trend) > 0.01:
            direction = "improving" if balance_trend > 0 else "degrading"
            trends.append(f"Load balance {direction}")
        
        if not trends:
            return "Usage patterns are stable over time"
        
        return "; ".join(trends)
    
    def reset_history(self):
        """Clear the usage history."""
        self.usage_history.clear()
    
    def export_history(self, filepath: str):
        """Export usage history to JSON file."""
        import json
        
        with open(filepath, 'w') as f:
            json.dump(self.usage_history, f, indent=2)
        
        print(f"Usage history exported to {filepath}") 
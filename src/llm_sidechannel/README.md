# LLM Sidechannel Analysis Package

A comprehensive Python package for analyzing Large Language Model (LLM) internals, with a focus on Mixture of Experts (MoE) architectures like Mixtral. This package provides tools to extract and analyze router decisions during inference, enabling deep insights into expert utilization patterns.

## Features

- **Mixtral MoE Analysis**: Specialized support for Mixtral 8x7B models with router logit extraction
- **Expert Usage Analytics**: Comprehensive analysis of expert utilization patterns
- **Modular Architecture**: Clean separation of concerns with core, models, analysis, and tools modules
- **Command-line Tools**: Ready-to-use CLI tools for querying and analyzing models
- **Multiple Configurations**: Pre-built configurations for different use cases and hardware constraints
- **Pattern Comparison**: Compare routing patterns across different prompts and contexts

## Architecture

```
llm_sidechannel/
├── core/                   # Core functionality
│   ├── mixtral_client.py   # High-level Mixtral client
│   ├── router_analyzer.py  # Router decision analysis
│   └── config.py          # Configuration management
├── models/                 # Model wrappers
│   └── mixtral_wrapper.py # Simplified Mixtral interface
├── analysis/              # Analysis utilities
│   └── expert_usage.py    # Expert usage pattern analysis
└── tools/                 # Command-line tools
    ├── query.py           # Interactive model querying
    └── analyze_moe.py     # Batch MoE analysis
```

## Installation

This package uses Nix for dependency management. The development environment includes all necessary dependencies including PyTorch, Transformers, and other ML libraries.

```bash
# Enter the development environment
nix develop

# The environment includes:
# - torch, transformers, tokenizers
# - accelerate, datasets
# - numpy, matplotlib, scipy
# - All existing SDR tools
```

## Quick Start

### 1. Configuration

List available model configurations:

```bash
python -m llm_sidechannel.tools.query --list-presets
```

Available presets:
- `mixtral-8x7b-instruct`: Standard Mixtral 8x7B Instruct model
- `mixtral-8x7b-4bit`: 4-bit quantized version (lower memory)
- `mixtral-8x7b-8bit`: 8-bit quantized version
- `mixtral-creative`: High temperature for creative generation
- `mixtral-precise`: Low temperature for factual responses

### 2. Basic Querying

Query a model with MoE analysis:

```bash
python -m llm_sidechannel.tools.query \
    --preset mixtral-8x7b-4bit \
    --prompt "Explain the concept of mixture of experts in machine learning" \
    --verbose
```

### 3. Pattern Analysis

Analyze routing patterns across multiple prompts:

```bash
python -m llm_sidechannel.tools.analyze_moe \
    --preset mixtral-8x7b-4bit \
    --prompts "Hello, how are you?" "Explain quantum computing" "Write a poem" \
    --compare \
    --output analysis_results.json
```

## Python API Usage

### Basic Usage

```python
from llm_sidechannel.core.config import load_model_config
from llm_sidechannel.models.mixtral_wrapper import MixtralWrapper

# Load configuration
config = load_model_config(preset="mixtral-8x7b-4bit")

# Create wrapper
wrapper = MixtralWrapper(config)

# Query with routing analysis
response = wrapper.query("Hello, how are you?", analyze_routing=True)

print(f"Response: {response.text}")
print(f"Expert usage: {response.expert_usage}")

# Get detailed analysis
analysis = wrapper.analyze_response(response)
summary = wrapper.get_expert_usage_summary(response)
print(summary)
```

### Advanced Analysis

```python
from llm_sidechannel.analysis.expert_usage import ExpertUsageAnalyzer

# Create analyzer
analyzer = ExpertUsageAnalyzer(num_experts=8)

# Analyze expert distribution
expert_usage = {0: 15, 1: 8, 2: 12, 3: 3, 4: 20, 5: 7, 6: 14, 7: 2}
analysis = analyzer.analyze_expert_distribution(expert_usage)

print(f"Entropy: {analysis['entropy']:.3f}")
print(f"Load balance score: {analysis['load_balance_score']:.3f}")
print(f"Analysis: {analysis['analysis']}")
```

### Pattern Comparison

```python
# Compare routing patterns across prompts
prompts = [
    "Write a technical explanation",
    "Tell me a story",
    "Solve a math problem"
]

comparison = wrapper.compare_prompts(prompts)
print(f"Pattern similarity: {comparison['comparison']['differences']['pattern_similarity']}")
```

## Configuration Options

### Model Configuration

```python
from llm_sidechannel.core.config import MixtralConfig

config = MixtralConfig(
    model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
    device="cuda",                    # or "cpu"
    torch_dtype=torch.float16,        # Precision
    load_in_4bit=True,               # Quantization
    max_new_tokens=200,              # Generation length
    temperature=0.7,                 # Sampling temperature
    top_p=0.9,                       # Nucleus sampling
    output_router_logits=True        # Enable MoE analysis
)
```

### Memory Requirements

Check memory requirements for different configurations:

```bash
python -m llm_sidechannel.tools.query --preset mixtral-8x7b-4bit --memory-info
```

Example output:
```
Memory Requirements:
  Model parameters: 46.7B
  Precision: 4-bit
  Model memory: ~23.4 GB
  Total memory: ~30.4 GB
  Recommendation: GPU with at least 24GB VRAM
```

## MoE Analysis Features

### Router Decision Analysis

- **Expert Selection**: Track which experts are selected for each token
- **Usage Patterns**: Analyze expert utilization across layers and tokens
- **Load Balancing**: Measure how evenly work is distributed across experts
- **Entropy Analysis**: Quantify the randomness in expert selection

### Metrics

- **Shannon Entropy**: Measures uniformity of expert usage
- **Gini Coefficient**: Measures inequality in expert utilization
- **Load Balance Score**: Quantifies how well-balanced the expert usage is
- **Correlation Analysis**: Compare routing patterns between different inputs

### Visualization and Export

- Export analysis results to JSON for further processing
- Generate summaries and reports
- Track usage patterns over time
- Compare routing decisions across different model configurations

## Integration with Existing Tools

The LLM sidechannel package integrates seamlessly with the existing SDR tools:

```bash
# SDR tools remain available
sdr-waterfall --help
sdr-verify-ptp --help

# New LLM tools
python -m llm_sidechannel.tools.query --help
python -m llm_sidechannel.tools.analyze_moe --help
```

## Hardware Requirements

### Minimum Requirements
- **4-bit quantization**: 24GB GPU memory
- **8-bit quantization**: 32GB GPU memory  
- **Full precision**: 64GB+ GPU memory

### Recommended Setup
- NVIDIA GPU with 40GB+ VRAM (A100, H100)
- 64GB+ system RAM
- Fast SSD storage for model caching

## Examples

See `test_llm_sidechannel.py` for a comprehensive example demonstrating:
- Configuration loading
- Expert usage analysis
- Model wrapper usage
- Pattern comparison

## Contributing

The package follows the same modular structure as the SDR experiments package:
- Add new models in `models/`
- Add new analysis techniques in `analysis/`
- Add new tools in `tools/`
- Core functionality goes in `core/`

## License

Same as the parent SDR experiments project. 
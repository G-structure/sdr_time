"""Configuration management for Mixtral models."""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Union
import torch


@dataclass
class MixtralConfig:
    """Configuration for Mixtral model loading and inference."""
    model_name: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    device: Optional[str] = None
    torch_dtype: Optional[torch.dtype] = None
    load_in_8bit: bool = False
    load_in_4bit: bool = False
    device_map: Optional[Union[str, Dict]] = "auto"
    trust_remote_code: bool = True
    output_router_logits: bool = True
    max_new_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: Optional[int] = None
    do_sample: bool = True


# Predefined configurations for different use cases
PRESET_CONFIGS = {
    "mixtral-8x7b-instruct": MixtralConfig(
        model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
        torch_dtype=torch.float16,
        load_in_4bit=False,
        max_new_tokens=100,
        temperature=0.7
    ),
    
    "mixtral-8x7b-base": MixtralConfig(
        model_name="mistralai/Mixtral-8x7B-v0.1",
        torch_dtype=torch.float16,
        load_in_4bit=False,
        max_new_tokens=100,
        temperature=0.7
    ),
    
    "mixtral-8x7b-4bit": MixtralConfig(
        model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
        torch_dtype=torch.float16,
        load_in_4bit=True,
        max_new_tokens=100,
        temperature=0.7
    ),
    
    "mixtral-8x7b-8bit": MixtralConfig(
        model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
        torch_dtype=torch.float16,
        load_in_8bit=True,
        max_new_tokens=100,
        temperature=0.7
    ),
    
    "mixtral-creative": MixtralConfig(
        model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
        torch_dtype=torch.float16,
        max_new_tokens=200,
        temperature=1.0,
        top_p=0.95,
        do_sample=True
    ),
    
    "mixtral-precise": MixtralConfig(
        model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
        torch_dtype=torch.float16,
        max_new_tokens=50,
        temperature=0.3,
        top_p=0.8,
        do_sample=True
    ),
}


def load_model_config(preset: Optional[str] = None, **kwargs) -> MixtralConfig:
    """
    Load a model configuration.
    
    Args:
        preset: Name of preset configuration to use
        **kwargs: Additional configuration overrides
        
    Returns:
        MixtralConfig object
    """
    if preset:
        if preset not in PRESET_CONFIGS:
            available = list(PRESET_CONFIGS.keys())
            raise ValueError(f"Unknown preset '{preset}'. Available presets: {available}")
        
        config = PRESET_CONFIGS[preset]
        
        # Apply any overrides
        if kwargs:
            config_dict = config.__dict__.copy()
            config_dict.update(kwargs)
            config = MixtralConfig(**config_dict)
    else:
        # Create config with defaults and overrides
        config = MixtralConfig(**kwargs)
    
    # Auto-detect device if not specified
    if config.device is None:
        config.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Set default torch_dtype if not specified
    if config.torch_dtype is None:
        config.torch_dtype = torch.float16 if config.device == "cuda" else torch.float32
    
    return config


def list_available_presets() -> Dict[str, str]:
    """
    List available configuration presets.
    
    Returns:
        Dictionary mapping preset names to descriptions
    """
    descriptions = {
        "mixtral-8x7b-instruct": "Standard Mixtral 8x7B Instruct model",
        "mixtral-8x7b-base": "Base Mixtral 8x7B model (not instruction-tuned)",
        "mixtral-8x7b-4bit": "Mixtral 8x7B Instruct with 4-bit quantization",
        "mixtral-8x7b-8bit": "Mixtral 8x7B Instruct with 8-bit quantization",
        "mixtral-creative": "High temperature for creative text generation",
        "mixtral-precise": "Low temperature for precise, factual responses",
    }
    return descriptions


def get_memory_requirements(config: MixtralConfig) -> Dict[str, str]:
    """
    Estimate memory requirements for a given configuration.
    
    Args:
        config: Model configuration
        
    Returns:
        Dictionary with memory estimates
    """
    base_params = 46.7e9  # Approximate parameters for Mixtral 8x7B
    
    if config.load_in_4bit:
        model_memory_gb = (base_params * 0.5) / 1e9  # ~0.5 bytes per parameter
        precision = "4-bit"
    elif config.load_in_8bit:
        model_memory_gb = (base_params * 1.0) / 1e9  # ~1 byte per parameter
        precision = "8-bit"
    elif config.torch_dtype == torch.float16:
        model_memory_gb = (base_params * 2.0) / 1e9  # ~2 bytes per parameter
        precision = "float16"
    else:
        model_memory_gb = (base_params * 4.0) / 1e9  # ~4 bytes per parameter
        precision = "float32"
    
    # Add overhead for inference
    total_memory_gb = model_memory_gb * 1.3  # 30% overhead
    
    return {
        "model_parameters": f"{base_params/1e9:.1f}B",
        "precision": precision,
        "model_memory_gb": f"{model_memory_gb:.1f}",
        "total_memory_gb": f"{total_memory_gb:.1f}",
        "recommendation": "GPU with at least 24GB VRAM" if total_memory_gb > 16 else "GPU with at least 16GB VRAM"
    } 
"""
error_handling_module.py

Reusable error handling utilities for AI Course Jupyter notebooks.
Use this as a reference or import it into your notebooks.

Example:
    # In your notebook cell
    %run error_handling_module.py

    # Then use in later cells
    validate_model_config(config)
    with gpu_memory_guard('my_model'):
        model = load_model('model.pt')
"""

import os
import sys
import time
import json
import torch
import traceback
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
from datetime import datetime


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class AILabError(Exception):
    """Base exception for AI course labs."""
    pass


class ConfigError(AILabError):
    """Configuration is invalid or incomplete."""
    pass


class DataError(AILabError):
    """Data loading or validation failed."""
    pass


class ModelError(AILabError):
    """Model loading or inference failed."""
    pass


class APIError(AILabError):
    """API call failed (rate limit, auth, network)."""
    pass


class ResourceError(AILabError):
    """Insufficient resources (memory, GPU)."""
    pass


# ============================================================================
# LOGGING & DIAGNOSTICS
# ============================================================================

class NotebookLogger:
    """Logger optimized for Jupyter educational context."""

    def __init__(self, name: str):
        self.name = name
        self.logs = []

    def concept(self, title: str, explanation: str):
        """Log a teaching point."""
        msg = f'\n📚 {title}\n{explanation}'
        print(msg)
        self.logs.append(('CONCEPT', title, explanation))

    def data(self, label: str, value):
        """Log data state (scalar or small array)."""
        if isinstance(value, (list, tuple)):
            summary = f'{type(value).__name__} with {len(value)} items'
        elif hasattr(value, 'shape'):
            summary = f'shape={value.shape}'
        else:
            summary = str(value)[:100]

        msg = f'📊 [{label}] {summary}'
        print(msg)
        self.logs.append(('DATA', label, value))

    def model(self, name: str, metric_name: str, value: float):
        """Log model metric."""
        msg = f'🧠 [{name}] {metric_name} = {value:.4f}'
        print(msg)
        self.logs.append(('MODEL', name, {metric_name: value}))

    def error(self, msg: str, suggestion: str = None):
        """Log error with fix."""
        full_msg = f'⚠️  {msg}'
        if suggestion:
            full_msg += f'\n   → {suggestion}'
        print(full_msg)
        self.logs.append(('ERROR', msg, suggestion))

    def perf(self, label: str, duration_sec: float):
        """Log performance metric."""
        if duration_sec < 1:
            duration_str = f'{duration_sec*1000:.0f} ms'
        else:
            duration_str = f'{duration_sec:.2f} s'
        msg = f'⏱️  [{label}] {duration_str}'
        print(msg)
        self.logs.append(('PERF', label, duration_sec))

    def summary(self):
        """Print summary of session."""
        print(f'\n{"="*60}')
        print(f'Session summary: {self.name}')
        print(f'{"="*60}')

        concepts = [log for log in self.logs if log[0] == 'CONCEPT']
        errors = [log for log in self.logs if log[0] == 'ERROR']

        if concepts:
            print(f'\n📚 Key concepts reviewed: {len(concepts)}')
        if errors:
            print(f'\n⚠️  Errors encountered and fixed: {len(errors)}')


def diagnose_notebook():
    """
    Print notebook diagnostic information.
    Use this when things break mysteriously.
    """
    print('='*60)
    print('NOTEBOOK DIAGNOSTICS')
    print('='*60)

    # Environment
    print('\n🔧 Environment:')
    print(f'  Python:       {sys.version.split()[0]}')
    print(f'  Notebook:     {"Jupyter" if "jupyter" in sys.modules else "Script"}')

    try:
        from google.colab import __version__
        print(f'  Colab:        Yes')
    except ImportError:
        print(f'  Colab:        No (local Jupyter)')

    # GPU
    print('\n💻 GPU/Memory:')
    if torch.cuda.is_available():
        print(f'  GPU Available: Yes ({torch.cuda.get_device_name(0)})')
        print(f'  CUDA Version:  {torch.version.cuda}')
        print(f'  GPU Memory:    {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
        print(f'  Memory Used:   {torch.cuda.memory_allocated() / 1e9:.1f} GB')
    else:
        print(f'  GPU Available: No (CPU only)')

    # Kernel state
    print('\n📦 Kernel State:')
    import gc
    print(f'  Live objects:  {len(gc.get_objects())}')
    print(f'  Variables:     {len([v for v in dir() if not v.startswith("_")])}')

    # Imports
    print('\n📚 Key Libraries:')
    for name in ['torch', 'transformers', 'anthropic', 'numpy', 'pandas']:
        try:
            mod = __import__(name)
            ver = getattr(mod, '__version__', 'installed')
            print(f'  {name:15s} {ver}')
        except ImportError:
            print(f'  {name:15s} NOT INSTALLED')

    # Recommendations
    print('\n💡 If things are broken:')
    print('  1. Kernel → Restart Kernel (clears all variables)')
    print('  2. Kernel → Restart Kernel and Run All Cells (proves it works)')
    print('  3. Check cell execution order (click a cell to see its number)')


# ============================================================================
# SECRET LOADING
# ============================================================================

def load_secret(name: str, required: bool = True) -> Optional[str]:
    """
    Load a secret from Colab Secrets or environment variables.

    Args:
        name: Secret name (e.g., 'ANTHROPIC_API_KEY')
        required: Raise error if not found (vs. return None)

    Returns:
        The secret value, or None if required=False and not found

    Raises:
        ValueError: If required=True and secret not found
    """
    # Try Colab Secrets (preferred in cloud)
    try:
        from google.colab import userdata
        try:
            value = userdata.get(name)
            print(f'✓ Loaded {name} from Colab Secrets')
            return value
        except userdata.SecretNotFoundError:
            pass
    except ImportError:
        pass

    # Fall back to environment variable
    value = os.environ.get(name)
    if value:
        print(f'✓ Loaded {name} from environment variable')
        return value

    # Not found anywhere
    if required:
        raise ValueError(
            f'{name} not found.\n\n'
            f'COLAB: Click the 🔑 icon, "Add new secret", name it "{name}".\n'
            f'LOCAL: export {name}=<value> before launching Jupyter Lab.\n'
            f'Get your key from: https://console.anthropic.com/api-keys'
        )
    return None


# ============================================================================
# VALIDATION
# ============================================================================

def validate_model_config(config: dict) -> dict:
    """
    Validate AI model configuration with layered checks.

    Args:
        config: Configuration dictionary

    Returns:
        Validated config

    Raises:
        KeyError, TypeError, ValueError with helpful messages
    """
    # Layer 1: Required keys
    required = {'model', 'temperature', 'max_tokens'}
    missing = required - set(config.keys())
    if missing:
        raise ConfigError(
            f'Config missing keys: {missing}\n'
            f'Expected: {required}\n'
            f'Got: {set(config.keys())}'
        )

    # Layer 2: Type validation
    if not isinstance(config['model'], str):
        raise ConfigError(
            f'config["model"] must be str, got {type(config["model"])}'
        )

    if not isinstance(config['temperature'], (int, float)):
        raise ConfigError(
            f'config["temperature"] must be number, got {type(config["temperature"])}'
        )

    # Layer 3: Value ranges
    if not (0 <= config['temperature'] <= 2):
        raise ConfigError(
            f'config["temperature"] must be in [0, 2], got {config["temperature"]}'
        )

    if not (1 <= config['max_tokens'] <= 4096):
        raise ConfigError(
            f'config["max_tokens"] must be in [1, 4096], got {config["max_tokens"]}'
        )

    # Layer 4: Semantic validation
    valid_models = ['claude-haiku-4-5', 'claude-sonnet-5', 'claude-opus-4-8']
    if config['model'] not in valid_models:
        raise ConfigError(
            f'config["model"] = {config["model"]} not recognized.\n'
            f'Supported: {valid_models}'
        )

    return config


def validate_dataset(data, allow_small: bool = False) -> bool:
    """
    Validate dataset with educational error messages.
    """
    if not isinstance(data, (list, tuple)):
        raise DataError(
            f'Expected list or tuple, got {type(data).__name__}\n'
            f'Example: data = [{{"text": "...", "label": "..."}}]'
        )

    if len(data) == 0:
        raise DataError(
            f'Dataset is empty.\n'
            f'Load your CSV first: df = pd.read_csv("data.csv")'
        )

    if not allow_small and len(data) < 10:
        print(f'⚠️  Warning: Only {len(data)} examples (aim for 100+)')

    # Check schema consistency
    first_keys = set(data[0].keys()) if isinstance(data[0], dict) else None
    if first_keys:
        for i, record in enumerate(data[1:], start=1):
            if isinstance(record, dict) and set(record.keys()) != first_keys:
                raise DataError(
                    f'Row {i} has different columns than row 0'
                )

    return True


# ============================================================================
# CONTEXT MANAGERS FOR RESOURCE MANAGEMENT
# ============================================================================

@contextmanager
def api_call_tracker(operation_name: str):
    """
    Track API call timing and errors.

    Usage:
        with api_call_tracker('sentiment_analysis'):
            response = client.messages.create(...)
    """
    start_time = time.time()
    print(f'[START] {operation_name}')

    try:
        yield
    except Exception as e:
        elapsed = time.time() - start_time
        print(f'[FAILED after {elapsed:.2f}s] {operation_name}: {type(e).__name__}')
        raise
    else:
        elapsed = time.time() - start_time
        print(f'[SUCCESS in {elapsed:.2f}s] {operation_name}')


@contextmanager
def gpu_memory_guard(model_name: str):
    """
    Guard against GPU OOM errors with automatic cleanup.

    Usage:
        with gpu_memory_guard('resnet50'):
            model = load_model()
    """
    if not torch.cuda.is_available():
        yield
        return

    initial_mem = torch.cuda.memory_allocated() / 1e6
    print(f'[GPU] Starting {model_name}: {initial_mem:.1f} MB used')

    try:
        yield
    except torch.cuda.OutOfMemoryError as e:
        final_mem = torch.cuda.memory_allocated() / 1e6
        raise ResourceError(
            f'GPU out of memory loading {model_name}.\n'
            f'Memory: {initial_mem:.1f} → {final_mem:.1f} MB\n'
            f'Fixes:\n'
            f'  1. Kernel → Restart Kernel\n'
            f'  2. Use smaller model\n'
            f'  3. Use CPU: model.to("cpu")\n'
            f'  4. Request GPU upgrade (Colab: Runtime → Change runtime type)'
        ) from e
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            final_mem = torch.cuda.memory_allocated() / 1e6
            print(f'[GPU] Cleaned up. Now: {final_mem:.1f} MB')


# ============================================================================
# MODEL UTILITIES
# ============================================================================

class ModelSession:
    """Context manager for safe model loading and cleanup."""

    def __init__(self, model_name: str, device: str = None):
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.tokenizer = None

    def __enter__(self):
        try:
            from transformers import AutoModel, AutoTokenizer

            print(f'Loading {self.model_name} on {self.device}...')
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            print(f'✓ Ready')
            return self
        except Exception as e:
            raise ModelError(f'Failed to load {self.model_name}: {e}') from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.model is not None:
            del self.model
        if self.tokenizer is not None:
            del self.tokenizer

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print('✓ Cleaned up model and memory')
        return False

    def predict(self, text: str):
        if self.model is None:
            raise RuntimeError('Model not loaded')

        inputs = self.tokenizer(text, return_tensors='pt').to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs


# ============================================================================
# DATA UTILITIES
# ============================================================================

class DatasetCache:
    """Cache datasets with version tracking to avoid stale data."""

    def __init__(self, cache_dir: str = '.cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_or_download(self, name: str, download_fn: Callable,
                       version: str = '1.0') -> list:
        """
        Load cached data or download if needed.

        Args:
            name: Dataset identifier
            download_fn: Function that returns the dataset
            version: Version string (to invalidate cache if format changes)

        Returns:
            The dataset
        """
        cache_file = self.cache_dir / f'{name}_v{version}.json'

        # Check cache
        if cache_file.exists():
            print(f'Loading cached {name}...')
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                print(f'✓ Loaded {len(data)} records from cache')
                return data
            except json.JSONDecodeError:
                print(f'⚠️  Cache corrupted, re-downloading...')
                cache_file.unlink()

        # Download
        print(f'Downloading {name}...')
        try:
            data = download_fn()

            # Save cache
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            print(f'✓ Downloaded and cached {len(data)} records')
            return data

        except Exception as e:
            raise DataError(
                f'Failed to download {name}: {type(e).__name__}\n'
                f'Check internet connection and try again.\n'
                f'Error: {e}'
            ) from e


# ============================================================================
# ERROR TESTING & DOCUMENTATION
# ============================================================================

class FailureModeCatalog:
    """
    Document expected failure modes and their fixes.
    Useful as a troubleshooting guide.
    """

    MODES = {
        'api_auth': {
            'error': 'anthropic.AuthenticationError',
            'cause': 'Invalid or expired API key',
            'symptoms': ['401 Unauthorized', 'Invalid API key'],
            'fixes': [
                'Go to https://console.anthropic.com/api-keys',
                'Create or copy your API key',
                'In Colab: add via 🔑 icon in sidebar',
                'Locally: export ANTHROPIC_API_KEY=... before jupyter lab'
            ]
        },
        'rate_limit': {
            'error': 'anthropic.RateLimitError',
            'cause': 'Too many API calls in short time',
            'symptoms': ['429 Too Many Requests'],
            'fixes': [
                'Wait 60 seconds before retrying',
                'Use cheaper model (haiku instead of opus)',
                'Check usage: https://console.anthropic.com'
            ]
        },
        'gpu_oom': {
            'error': 'torch.cuda.OutOfMemoryError',
            'cause': 'Model too large for available GPU memory',
            'symptoms': ['CUDA out of memory'],
            'fixes': [
                'Restart kernel: Kernel → Restart Kernel',
                'Use smaller model variant',
                'Use CPU: model.to("cpu")',
                'Request larger GPU'
            ]
        },
    }

    @classmethod
    def explain(cls, error_type: str):
        """Print explanation of a failure mode."""
        if error_type not in cls.MODES:
            print(f'Unknown: {error_type}')
            print(f'Known: {", ".join(cls.MODES.keys())}')
            return

        mode = cls.MODES[error_type]
        print(f'\n{"="*60}')
        print(f'Failure Mode: {error_type}')
        print(f'{"="*60}')
        print(f'Error: {mode["error"]}')
        print(f'Cause: {mode["cause"]}')
        print(f'\nSymptoms:')
        for symptom in mode['symptoms']:
            print(f'  • {symptom}')
        print(f'\nFixes:')
        for i, fix in enumerate(mode['fixes'], 1):
            print(f'  {i}. {fix}')
        print()


def test_error_handling():
    """
    Verify that error handling works as expected.
    Use this to teach students that errors are intentional.
    """

    print('Testing error scenarios...\n')

    # Test 1: Missing API key
    print('[Test 1] Missing API key')
    try:
        load_secret('NONEXISTENT_KEY_XYZ', required=True)
        print('❌ FAILED: Should have raised error')
    except ValueError as e:
        if 'Colab' in str(e) and 'environment' in str(e):
            print('✓ PASSED: Clear error with fixes')
        else:
            print(f'⚠️  PARTIAL: {str(e)[:100]}')

    # Test 2: Invalid config
    print('\n[Test 2] Invalid config')
    bad_config = {'model': 'invalid', 'temperature': 5}
    try:
        validate_model_config(bad_config)
        print('❌ FAILED: Should have raised error')
    except ConfigError as e:
        print('✓ PASSED: Caught invalid config')

    # Test 3: Empty dataset
    print('\n[Test 3] Empty dataset')
    try:
        validate_dataset([])
        print('❌ FAILED: Should have raised error')
    except DataError as e:
        print('✓ PASSED: Caught empty data')

    # Test 4: Valid config
    print('\n[Test 4] Valid config')
    good_config = {
        'model': 'claude-opus-4-8',
        'temperature': 0.5,
        'max_tokens': 512
    }
    try:
        result = validate_model_config(good_config)
        print('✓ PASSED: Valid config accepted')
    except Exception as e:
        print(f'❌ FAILED: {e}')

    print('\n' + '='*60)


# ============================================================================
# MAIN - Run tests if executed directly
# ============================================================================

if __name__ == '__main__':
    print('AI Course Error Handling Module')
    print('='*60)
    print('\nUsage in Jupyter notebook:')
    print('  %run error_handling_module.py')
    print('\nOr import:')
    print('  from error_handling_module import *')
    print('\n' + '='*60)
    print('\nRunning diagnostic tests...\n')

    diagnose_notebook()
    print('\n')
    test_error_handling()

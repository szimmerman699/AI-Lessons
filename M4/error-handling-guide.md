# Error Handling Best Practices for AI Course Jupyter Notebooks

## Executive Summary

This guide provides comprehensive error handling patterns for a Python-based AI course using Jupyter notebooks. It emphasizes:
- **Educational clarity** — errors should teach, not confuse
- **Jupyter-specific gotchas** — state management, kernel restarts, async issues
- **ML/AI scenarios** — API failures, model loading, data validation, resource constraints
- **Production-grade practices** — patterns that scale from notebooks to real systems
- **Testing error paths** — explicit failure verification for learning

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Exception Handling Patterns](#exception-handling-patterns)
3. [Input Validation & User-Friendly Messages](#input-validation--user-friendly-messages)
4. [Common AI/ML Failure Scenarios](#common-aiml-failure-scenarios)
5. [Resource Management & Cleanup](#resource-management--cleanup)
6. [Logging for Learning](#logging-for-learning)
7. [Debugging Strategies](#debugging-strategies)
8. [Testing Error Paths](#testing-error-paths)
9. [Patterns from Popular Libraries](#patterns-from-popular-libraries)
10. [Gotchas & Anti-Patterns](#gotchas--anti-patterns)

---

## Core Principles

### 1. **Errors Are Teaching Moments**

In an educational context, an error message should:
- Name the problem concretely
- Explain WHY it happened (architectural/mechanical reason)
- Show exactly how to fix it
- Link to relevant course material

**Example:**
```python
# BAD: Generic error
assert api_key, 'API key not found'

# GOOD: Educational error
assert ANTHROPIC_API_KEY, (
    'ANTHROPIC_API_KEY not found.\n\n'
    'Why: The notebook needs to authenticate with Anthropic.\n\n'
    'How to fix:\n'
    '  1. In Colab: Click the key icon in the left sidebar\n'
    '  2. Click "Add new secret"\n'
    '  3. Name: ANTHROPIC_API_KEY (exact case)\n'
    '  4. Paste your key from https://console.anthropic.com\n'
    '  5. Toggle "Notebook access" ON\n'
    '  6. Re-run this cell\n\n'
    'See M1-L0-notebooks-for-ai-work.ipynb for details.'
)
```

### 2. **Fail Early, Fail Loudly**

Don't silently swallow errors. In a learning context, hidden failures are worse than loud ones.

```python
# BAD: Silent failure
def load_model(path):
    try:
        return torch.load(path)
    except:  # Don't do this
        return None

# GOOD: Explicit failure
def load_model(path):
    try:
        return torch.load(path)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f'Model not found at {path}.\n'
            f'Expected location: {Path(path).resolve()}\n'
            f'Tip: Download from https://huggingface.co/models/...'
        ) from e
    except torch.cuda.OutOfMemoryError as e:
        raise RuntimeError(
            f'GPU out of memory.\n'
            f'Model size may exceed your GPU memory.\n'
            f'Options:\n'
            f'  1. Use CPU: model.to("cpu")\n'
            f'  2. Use smaller model variant\n'
            f'  3. Reduce batch size'
        ) from e
```

### 3. **Context Matters**

Notebook vs. production code have different error handling strategies:

| Aspect | Notebook | Production |
|--------|----------|-----------|
| **Failure mode** | User should understand it | System should recover |
| **Logging** | Print + visual markers | Structured logs → monitoring |
| **Retry strategy** | Explicit (user re-runs cell) | Automatic with backoff |
| **Resource cleanup** | Often manual | Guaranteed (context managers) |
| **State** | Accumulated in kernel | Fresh per request |

---

## Exception Handling Patterns

### Pattern 1: Dual-Path Loading (Colab + Local)

Your notebooks work in two environments. Handle both gracefully.

```python
def load_secret(name: str, required: bool = True) -> str:
    """
    Load a secret from Colab Secrets or environment variables.
    
    Args:
        name: Secret name (e.g., 'ANTHROPIC_API_KEY')
        required: Raise error if not found (vs. return None)
    
    Returns:
        The secret value
    
    Raises:
        ValueError: If required=True and secret not found
    
    Why this pattern:
        Same notebook runs in Colab (via Secrets Manager) and locally
        (via shell environment). Try Colab first, fall back to env var.
    """
    # Try Colab Secrets (preferred in cloud)
    try:
        from google.colab import userdata
        try:
            value = userdata.get(name)
            print(f'✓ Loaded {name} from Colab Secrets')
            return value
        except userdata.SecretNotFoundError:
            pass  # Fall through to env var
    except ImportError:
        pass  # Not in Colab, check env var
    
    # Fall back to environment variable (preferred locally)
    value = os.environ.get(name)
    if value:
        print(f'✓ Loaded {name} from environment variable')
        return value
    
    # Not found anywhere
    if required:
        raise ValueError(
            f'{name} not found.\n\n'
            f'COLAB: Click the 🔑 icon in the left sidebar, '
            f'"Add new secret", name it exactly "{name}", paste the value.\n\n'
            f'LOCAL: export {name}=<your-value> before launching Jupyter Lab.\n\n'
            f'Get your key from: https://console.anthropic.com/api-keys'
        )
    return None


# Usage
ANTHROPIC_API_KEY = load_secret('ANTHROPIC_API_KEY')
```

### Pattern 2: Layered Validation

Validate at multiple levels: early checks, type checks, semantic checks.

```python
def validate_model_config(config: dict) -> dict:
    """
    Validate AI model configuration.
    
    Layers:
    1. Required keys present
    2. Types correct
    3. Values in valid range
    4. Semantic consistency
    
    Returns the validated config or raises detailed error.
    """
    # Layer 1: Required keys
    required = {'model', 'temperature', 'max_tokens'}
    missing = required - set(config.keys())
    if missing:
        raise KeyError(
            f'Config missing keys: {missing}\n'
            f'Expected: {required}\n'
            f'Got: {set(config.keys())}'
        )
    
    # Layer 2: Type validation
    if not isinstance(config['model'], str):
        raise TypeError(
            f'config["model"] must be str, got {type(config["model"])}\n'
            f'Example: "claude-opus-4-8"'
        )
    
    if not isinstance(config['temperature'], (int, float)):
        raise TypeError(
            f'config["temperature"] must be number, got {type(config["temperature"])}'
        )
    
    # Layer 3: Value range validation
    if not (0 <= config['temperature'] <= 2):
        raise ValueError(
            f'config["temperature"] must be in [0, 2], got {config["temperature"]}\n'
            f'Interpretation:\n'
            f'  0 = deterministic (best for tasks requiring accuracy)\n'
            f'  1 = balanced (default, good for exploration)\n'
            f'  2 = highly random (good for creative tasks)'
        )
    
    if not (1 <= config['max_tokens'] <= 4096):
        raise ValueError(
            f'config["max_tokens"] must be in [1, 4096], got {config["max_tokens"]}'
        )
    
    # Layer 4: Semantic validation
    if config['model'] not in ['claude-haiku-4-5', 'claude-sonnet-5', 'claude-opus-4-8']:
        raise ValueError(
            f'config["model"] = {config["model"]} not recognized.\n'
            f'Supported models:\n'
            f'  - claude-haiku-4-5 (fastest, cheapest)\n'
            f'  - claude-sonnet-5 (balanced)\n'
            f'  - claude-opus-4-8 (most capable)'
        )
    
    return config
```

### Pattern 3: Context Managers for Setup/Teardown

Ensure resources are released even if code fails.

```python
from contextlib import contextmanager
import time

@contextmanager
def api_call_tracker(operation_name: str):
    """
    Track API call timing and errors for debugging.
    
    Why this pattern:
        API calls can fail silently (timeout, rate limit).
        Tracking helps students understand performance characteristics.
    
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
def gpu_memory_guard(model_name: str, max_mb: int = 2000):
    """
    Guard against GPU OOM errors.
    
    Why this pattern:
        Notebooks can accumulate GPU memory (kernel state).
        This catches OOM early and suggests fixes.
    """
    import torch
    
    initial_mem = torch.cuda.memory_allocated() / 1e6 if torch.cuda.is_available() else 0
    print(f'[GPU] Starting {model_name}: {initial_mem:.1f} MB used')
    
    try:
        yield
    except torch.cuda.OutOfMemoryError as e:
        final_mem = torch.cuda.memory_allocated() / 1e6 if torch.cuda.is_available() else 0
        raise RuntimeError(
            f'GPU out of memory loading {model_name}.\n'
            f'Memory before: {initial_mem:.1f} MB\n'
            f'Memory after failed attempt: {final_mem:.1f} MB\n'
            f'Max available: ~{torch.cuda.get_device_properties(0).total_memory / 1e6:.0f} MB\n\n'
            f'Fixes:\n'
            f'  1. Restart kernel: Kernel → Restart Kernel → clear all state\n'
            f'  2. Use smaller model: e.g., clip-vit-base instead of clip-vit-large\n'
            f'  3. Use CPU: model.to("cpu")\n'
            f'  4. Request GPU upgrade in Colab: Runtime → Change runtime type → GPU'
        ) from e
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            final_mem = torch.cuda.memory_allocated() / 1e6
            print(f'[GPU] Cleaned up. Now using: {final_mem:.1f} MB')


# Usage
with gpu_memory_guard('ResNet50'):
    model = torch.hub.load('pytorch/vision:v0.10.0', 'resnet50', pretrained=True)
```

### Pattern 4: Custom Exception Hierarchy

Domain-specific exceptions make debugging easier.

```python
class AILabError(Exception):
    """Base exception for the AI course labs."""
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


# Usage with helpful context
def call_api(prompt: str, max_retries: int = 3):
    """
    Call Anthropic API with retry logic and clear error reporting.
    """
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model='claude-opus-4-8',
                max_tokens=512,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return response
        except anthropic.RateLimitError as e:
            if attempt == max_retries - 1:
                raise APIError(
                    f'Rate limit exceeded after {max_retries} retries.\n'
                    f'This means we\'ve hit API quotas.\n'
                    f'Options:\n'
                    f'  1. Wait 60 seconds and re-run this cell\n'
                    f'  2. Use a cheaper model (haiku instead of opus)\n'
                    f'  3. Check usage at https://console.anthropic.com'
                ) from e
            wait_time = 2 ** attempt  # Exponential backoff
            print(f'[Attempt {attempt + 1}/{max_retries}] Rate limited. '
                  f'Waiting {wait_time}s before retry...')
            time.sleep(wait_time)
        except anthropic.AuthenticationError as e:
            raise APIError(
                f'Authentication failed.\n'
                f'Your ANTHROPIC_API_KEY is invalid or expired.\n'
                f'Fix: Get a new key from https://console.anthropic.com/api-keys'
            ) from e
        except Exception as e:
            raise ModelError(
                f'Unexpected error calling API: {type(e).__name__}: {e}'
            ) from e
```

---

## Input Validation & User-Friendly Error Messages

### Anti-Pattern: Generic Errors

```python
# ❌ BAD
assert len(data) > 0, 'No data'
assert model_name in models, 'Invalid model'
```

### Pattern: Contextual, Actionable Errors

```python
def validate_dataset(data):
    """
    Validate dataset with educational error messages.
    """
    if not isinstance(data, (list, tuple)):
        raise DataError(
            f'Expected data to be list or tuple, got {type(data).__name__}.\n'
            f'Example:\n'
            f'  data = [{{"text": "...", "label": "..."}}]\n'
            f'  validate_dataset(data)'
        )
    
    if len(data) == 0:
        raise DataError(
            f'Dataset is empty.\n'
            f'Why this matters: We need examples to train/evaluate.\n'
            f'How to fix: Load your CSV first:\n'
            f'  import pandas as pd\n'
            f'  df = pd.read_csv("data.csv")\n'
            f'  data = df.to_dict("records")\n'
            f'  validate_dataset(data)'
        )
    
    if len(data) < 10:
        print(f'⚠️  Warning: Dataset has only {len(data)} examples.')
        print(f'   For robust ML, aim for 100+ examples.')
        print(f'   Continue anyway? Call validate_dataset(..., allow_small=True)')
    
    # Check schema consistency
    first_keys = set(data[0].keys())
    for i, record in enumerate(data[1:], start=1):
        if set(record.keys()) != first_keys:
            raise DataError(
                f'Row {i} has different columns than row 0.\n'
                f'Row 0 columns: {first_keys}\n'
                f'Row {i} columns: {set(record.keys())}\n'
                f'All rows must have the same schema (keys).'
            )
    
    return True
```

---

## Common AI/ML Failure Scenarios

### Scenario 1: API Authentication Failures

```python
def setup_api_client(api_key: str = None):
    """
    Initialize Anthropic client with clear error handling.
    """
    try:
        # Try to use provided key, or fall back to environment
        key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        
        if not key:
            raise ValueError('No API key found')
        
        client = anthropic.Anthropic(api_key=key)
        
        # Test the connection
        _ = client.messages.count_tokens(
            model='claude-opus-4-8',
            messages=[{'role': 'user', 'content': 'test'}]
        )
        
        print('✓ API authentication successful')
        return client
    
    except anthropic.AuthenticationError as e:
        raise APIError(
            f'API authentication failed.\n'
            f'Your ANTHROPIC_API_KEY is invalid.\n\n'
            f'How to fix:\n'
            f'  1. Go to https://console.anthropic.com/api-keys\n'
            f'  2. Create or copy an existing API key\n'
            f'  3a. In Colab: Add it via the key icon → "Add new secret"\n'
            f'  3b. Locally: export ANTHROPIC_API_KEY=<key> before launching Jupyter\n'
            f'  4. Re-run this cell'
        ) from e
    except Exception as e:
        raise APIError(
            f'Unexpected error setting up API client: {type(e).__name__}\n'
            f'Error details: {e}'
        ) from e
```

### Scenario 2: Model Not Found / Failed to Load

```python
def load_transformer_model(model_name: str, device: str = 'cpu'):
    """
    Load a Hugging Face transformer with educational error handling.
    """
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    
    try:
        print(f'Loading {model_name}...')
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        model.to(device)
        print(f'✓ Loaded {model_name} on {device}')
        return model, tokenizer
    
    except OSError as e:
        # Model not found (typo or doesn't exist)
        raise ModelError(
            f'Model "{model_name}" not found on Hugging Face.\n\n'
            f'Did you mean one of these?\n'
            f'  - distilbert-base-uncased-finetuned-sst-2-english\n'
            f'  - bert-base-uncased\n'
            f'  - roberta-base\n\n'
            f'Search all models:\n'
            f'  https://huggingface.co/models?task=text-classification\n\n'
            f'Error: {e}'
        ) from e
    
    except torch.cuda.OutOfMemoryError as e:
        raise ResourceError(
            f'GPU out of memory loading {model_name}.\n'
            f'Options:\n'
            f'  1. Restart kernel and use CPU: device="cpu"\n'
            f'  2. Use a smaller model: "distilbert-base-..." instead\n'
            f'  3. Request GPU upgrade (Colab: Runtime → Change runtime type → GPU)'
        ) from e


# Usage
model, tokenizer = load_transformer_model(
    'distilbert-base-uncased-finetuned-sst-2-english',
    device='cuda' if torch.cuda.is_available() else 'cpu'
)
```

### Scenario 3: Data Loading & Validation

```python
def load_csv_data(filepath: str, expected_columns: list = None):
    """
    Load CSV with validation and helpful error messages.
    """
    import pandas as pd
    
    # Check file exists
    if not Path(filepath).exists():
        raise DataError(
            f'File not found: {filepath}\n'
            f'Current working directory: {Path.cwd()}\n'
            f'Files here:\n'
            + '\n'.join(f'  - {f}' for f in Path.cwd().glob('*.csv')[:5])
        )
    
    # Try to load
    try:
        df = pd.read_csv(filepath)
    except pd.errors.ParserError as e:
        raise DataError(
            f'CSV parsing failed for {filepath}.\n'
            f'This usually means:\n'
            f'  1. Encoding issue (try encoding="latin1" or "utf-16")\n'
            f'  2. Delimiter mismatch (is it comma, tab, semicolon?)\n'
            f'  3. Corrupted file\n\n'
            f'Try: pd.read_csv("{filepath}", encoding="latin1")\n\n'
            f'Error: {e}'
        ) from e
    
    # Validate schema
    if expected_columns:
        missing = set(expected_columns) - set(df.columns)
        if missing:
            raise DataError(
                f'CSV missing columns: {missing}\n'
                f'Expected: {expected_columns}\n'
                f'Found: {list(df.columns)}'
            )
    
    # Validate content
    if df.empty:
        raise DataError('CSV file is empty (no rows)')
    
    if df.isnull().all().any():
        null_cols = df.columns[df.isnull().all()].tolist()
        raise DataError(
            f'These columns are entirely null: {null_cols}\n'
            f'Is your CSV formatted correctly?'
        )
    
    print(f'✓ Loaded {len(df)} rows, {len(df.columns)} columns')
    return df
```

### Scenario 4: Inference & Prediction Errors

```python
def predict_sentiment(text: str, model, tokenizer):
    """
    Make predictions with validation and error recovery.
    
    Why this pattern:
        Model inference can fail for various reasons:
        - Text too long
        - Invalid tokens
        - Device mismatch (GPU/CPU)
        Each needs a specific fix.
    """
    try:
        # Validate input
        if not text or not isinstance(text, str):
            raise ValueError('text must be non-empty string')
        
        if len(text) > 512:
            print(f'⚠️  Text is {len(text)} chars. Truncating to 512...')
            text = text[:512]
        
        # Tokenize
        inputs = tokenizer(text, return_tensors='pt', truncation=True)
        
        # Move to model device
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Predict
        with torch.no_grad():
            outputs = model(**inputs)
        
        # Parse results
        logits = outputs.logits[0]
        probs = torch.softmax(logits, dim=-1)
        pred_idx = probs.argmax().item()
        pred_label = model.config.id2label[pred_idx]
        confidence = probs[pred_idx].item()
        
        return {
            'label': pred_label,
            'confidence': confidence,
            'scores': {model.config.id2label[i]: p.item() 
                      for i, p in enumerate(probs)}
        }
    
    except RuntimeError as e:
        if 'out of memory' in str(e).lower():
            raise ResourceError(
                'GPU out of memory during inference.\n'
                'Restart kernel to clear state: Kernel → Restart Kernel'
            ) from e
        raise
    except Exception as e:
        raise ModelError(
            f'Prediction failed: {type(e).__name__}\n'
            f'Input: {text[:100]}...\n'
            f'Error: {e}'
        ) from e
```

---

## Resource Management & Cleanup

### Pattern: Explicit Resource Cleanup

In notebooks, students often forget to clean up resources. Make it explicit.

```python
class ModelSession:
    """
    Context manager for safe model loading and cleanup.
    
    Usage:
        with ModelSession('bert-base-uncased') as session:
            output = session.predict(text)
        # Model is cleaned up automatically
    """
    
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
        return False  # Don't suppress exceptions
    
    def predict(self, text: str):
        if self.model is None:
            raise RuntimeError('Model not loaded. Use `with ModelSession(...) as session:`')
        
        inputs = self.tokenizer(text, return_tensors='pt').to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs


# Usage: guaranteed cleanup even if prediction fails
try:
    with ModelSession('bert-base-uncased') as session:
        result = session.predict('Hello world')
        print(result)
except Exception as e:
    print(f'Error: {e}')
# Model is cleaned up regardless
```

### Pattern: Jupyter-Safe Dataset Caching

```python
from pathlib import Path
import json
from datetime import datetime

class DatasetCache:
    """
    Cache datasets with version tracking.
    
    Why this pattern:
        Downloading datasets every time slows notebooks.
        But stale caches can cause bugs.
        Track versions to catch inconsistencies.
    """
    
    def __init__(self, cache_dir: str = '.cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_or_download(self, name: str, download_fn, version: str = '1.0'):
        """
        Load cached data or download if needed.
        
        Args:
            name: Dataset identifier
            download_fn: Function that returns the dataset
            version: Version string (to invalidate cache if format changes)
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
            except json.JSONDecodeError as e:
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
                f'Error: {e}\n'
                f'Check your internet connection and try again.'
            ) from e


# Usage
cache = DatasetCache('.data')

def fetch_imdb():
    from datasets import load_dataset
    ds = load_dataset('imdb')
    return ds['train'][:1000]

train_data = cache.get_or_download(
    'imdb_train',
    fetch_imdb,
    version='1.0'
)
```

---

## Logging for Learning

### Pattern: Educational Logging (Not Just Debugging)

```python
import logging
from datetime import datetime
from enum import Enum

class LogLevel(Enum):
    """Log levels appropriate for educational notebooks."""
    CONCEPT = 'CONCEPT'  # Teaching point
    DATA = 'DATA'        # Data state
    MODEL = 'MODEL'      # Model behavior
    ERROR = 'ERROR'      # Problems
    PERF = 'PERF'        # Performance metric

class NotebookLogger:
    """
    Logger for Jupyter notebooks that emphasizes learning.
    
    Differs from production logging:
    - Teaches concepts alongside events
    - Visualizes data state
    - Emphasizes human understanding over machine parsing
    """
    
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


# Usage
logger = NotebookLogger('M2 L3 - Sentiment Analysis')

logger.concept(
    'Why Transformers Outperform Earlier NLP',
    'Transformers use attention to see all words at once, '
    'instead of one word at a time (like RNN). This parallelizes training '
    'and captures long-range relationships.'
)

logger.data('texts', ['Great movie!', 'Terrible acting'])
logger.model('DistilBERT', 'accuracy', 0.92)
logger.perf('Model loading', 2.34)

if some_error:
    logger.error(
        'Batch size too large for GPU',
        'Try batch_size=8 instead of 32'
    )

logger.summary()
```

---

## Debugging Strategies

### Strategy 1: Systematic Kernel Inspection

```python
def diagnose_notebook():
    """
    Print notebook diagnostic information.
    
    Use this when things break mysteriously.
    """
    import sys
    import torch
    import numpy as np
    
    print('='*60)
    print('NOTEBOOK DIAGNOSTICS')
    print('='*60)
    
    # Environment
    print('\n🔧 Environment:')
    print(f'  Python:       {sys.version.split()[0]}')
    print(f'  Jupyter:      {get_ipython().__class__.__name__ if "get_ipython" in dir() else "Not in Jupyter"}')
    
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
            print(f'  {name:15s} {mod.__version__ if hasattr(mod, "__version__") else "installed"}')
        except ImportError:
            print(f'  {name:15s} NOT INSTALLED')
    
    # Recommendations
    print('\n💡 If things are broken:')
    print('  1. Kernel → Restart Kernel (clears all variables)')
    print('  2. Kernel → Restart Kernel and Run All Cells (proves it works top-to-bottom)')
    print('  3. Check cell execution order (click a cell, see its number)')
    print('  4. Run this cell to verify the environment')


# Usage when things break
diagnose_notebook()
```

### Strategy 2: Step-by-Step Execution Tracing

```python
def trace_execution(func, *args, **kwargs):
    """
    Run function with detailed logging at each step.
    
    Useful for understanding where errors occur.
    """
    import traceback
    
    print(f'Tracing: {func.__name__}({args}, {kwargs})')
    print('=' * 60)
    
    try:
        # Instrument function
        import sys
        
        def trace_calls(frame, event, arg):
            if event == 'call':
                code = frame.f_code
                if 'notebooks' in code.co_filename or '<' in code.co_filename:
                    print(f'  → {code.co_name} ({code.co_filename}:{frame.f_lineno})')
            return trace_calls
        
        sys.settrace(trace_calls)
        result = func(*args, **kwargs)
        sys.settrace(None)
        
        print('=' * 60)
        print(f'✓ Completed successfully')
        return result
    
    except Exception as e:
        sys.settrace(None)
        print('=' * 60)
        print(f'✗ Failed with {type(e).__name__}:')
        traceback.print_exc()
        raise


# Usage
def complex_pipeline(data):
    result = preprocess(data)
    result = model_inference(result)
    result = postprocess(result)
    return result

# trace_execution(complex_pipeline, my_data)
```

---

## Testing Error Paths

### Pattern: Explicit Failure Testing

Students should test that errors work correctly.

```python
def test_error_handling():
    """
    Verify that error handling works as expected.
    
    This is a teaching tool: students see that errors
    are intentional and informative, not accidental.
    """
    
    print('Testing error scenarios...\n')
    
    # Test 1: Missing API key
    print('[Test 1] Missing API key')
    try:
        load_secret('NONEXISTENT_KEY', required=True)
        print('❌ FAILED: Should have raised error')
    except ValueError as e:
        if 'Colab' in str(e) and 'environment' in str(e):
            print('✓ PASSED: Clear error message with fixes')
        else:
            print(f'❌ FAILED: Wrong error message: {e}')
    
    # Test 2: Invalid config
    print('\n[Test 2] Invalid config')
    bad_config = {'model': 'invalid', 'temperature': 5}  # temp out of range
    try:
        validate_model_config(bad_config)
        print('❌ FAILED: Should have raised error')
    except (KeyError, TypeError, ValueError) as e:
        if 'temperature' in str(e) and '[0, 2]' in str(e):
            print('✓ PASSED: Caught out-of-range temperature')
        else:
            print(f'⚠️  PARTIAL: Caught error but message could be better: {e}')
    
    # Test 3: Empty dataset
    print('\n[Test 3] Empty dataset')
    try:
        validate_dataset([])
        print('❌ FAILED: Should have raised error')
    except DataError as e:
        if 'empty' in str(e).lower():
            print('✓ PASSED: Clear error on empty data')
        else:
            print(f'⚠️  PARTIAL: {e}')
    
    # Test 4: Successful path
    print('\n[Test 4] Valid config')
    good_config = {'model': 'claude-opus-4-8', 'temperature': 0.5, 'max_tokens': 512}
    try:
        result = validate_model_config(good_config)
        print('✓ PASSED: Valid config accepted')
    except Exception as e:
        print(f'❌ FAILED: Should not raise error: {e}')
    
    print('\n' + '='*60)
    print('Error handling tests complete')


# Run tests
# test_error_handling()
```

### Pattern: Failure Mode Catalog

```python
class FailureModeCatalog:
    """
    Document expected failure modes and their fixes.
    
    This teaches students what can go wrong and how
    to diagnose it. Think of it as a troubleshooting guide.
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
                'Batch requests to reduce frequency',
                'Check usage: https://console.anthropic.com'
            ]
        },
        'gpu_oom': {
            'error': 'torch.cuda.OutOfMemoryError',
            'cause': 'Model too large for available GPU memory',
            'symptoms': ['CUDA out of memory', 'Allocation failed'],
            'fixes': [
                'Restart kernel: Kernel → Restart Kernel',
                'Use smaller model variant',
                'Reduce batch size',
                'Use CPU instead: model.to("cpu")',
                'Request larger GPU (Colab: Runtime → Change runtime type)'
            ]
        },
        'model_not_found': {
            'error': 'OSError (from transformers)',
            'cause': 'Model name misspelled or doesn\'t exist',
            'symptoms': ['Cannot find model', 'HF_HUB_OFFLINE'],
            'fixes': [
                'Check model name spelling',
                'Search huggingface.co/models',
                'Verify internet connection',
                'Use known model: distilbert-base-uncased'
            ]
        }
    }
    
    @classmethod
    def explain(cls, error_type: str):
        """Print explanation of a failure mode."""
        if error_type not in cls.MODES:
            print(f'Unknown error type: {error_type}')
            print(f'Known types: {", ".join(cls.MODES.keys())}')
            return
        
        mode = cls.MODES[error_type]
        print(f'\n{"="*60}')
        print(f'Failure Mode: {error_type}')
        print(f'{"="*60}')
        print(f'\nError Class: {mode["error"]}')
        print(f'Root Cause: {mode["cause"]}')
        print(f'\nSymptoms:')
        for symptom in mode['symptoms']:
            print(f'  • {symptom}')
        print(f'\nHow to Fix:')
        for i, fix in enumerate(mode['fixes'], 1):
            print(f'  {i}. {fix}')
        print()


# Usage
FailureModeCatalog.explain('api_auth')
FailureModeCatalog.explain('gpu_oom')
```

---

## Patterns from Popular Libraries

### Pattern 1: PyTorch Model Loading Errors

```python
# PyTorch's approach: specific exception types with recovery hints

import torch
from torch import nn

def load_checkpoint(path: str, model: nn.Module, device: str = 'cpu'):
    """
    Load PyTorch checkpoint with error recovery.
    
    PyTorch's philosophy:
    - Be explicit about device placement
    - Warn about shape mismatches
    - Suggest alternatives
    """
    try:
        checkpoint = torch.load(path, map_location=device)
    except FileNotFoundError:
        raise FileNotFoundError(
            f'Checkpoint not found: {path}\n'
            f'Current dir: {Path.cwd()}\n'
            f'Available .pt files: {list(Path.cwd().glob("*.pt"))}'
        )
    except torch.cuda.OutOfMemoryError:
        raise RuntimeError(
            f'GPU out of memory loading checkpoint.\n'
            f'Try: torch.load(..., map_location="cpu") then model.to("cuda")'
        )
    except Exception as e:
        raise RuntimeError(
            f'Failed to load checkpoint: {type(e).__name__}\n'
            f'Path: {path}\n'
            f'Error: {e}'
        ) from e
    
    try:
        model.load_state_dict(checkpoint['model_state_dict'])
    except KeyError:
        raise KeyError(
            f'Checkpoint does not have "model_state_dict".\n'
            f'Keys in checkpoint: {list(checkpoint.keys())}'
        )
    except RuntimeError as e:
        if 'size mismatch' in str(e):
            raise RuntimeError(
                f'Model shape mismatch. Your model and the checkpoint '
                f'have different architectures.\n'
                f'Error: {e}\n'
                f'Fix: Ensure model definition matches checkpoint'
            ) from e
        raise
    
    return model.to(device)
```

### Pattern 2: Scikit-learn Input Validation

```python
# scikit-learn's approach: validate before expensive operations

def check_input_data(X, y=None, task='classification'):
    """
    Validate input data like scikit-learn does.
    
    scikit-learn philosophy:
    - Validate early (before training)
    - Be specific about what's wrong
    - Suggest the correct format
    """
    import numpy as np
    
    # Check X type and shape
    if not isinstance(X, (np.ndarray, list)):
        raise TypeError(
            f'X must be numpy array or list, got {type(X)}.\n'
            f'Example: X = np.array([[1, 2], [3, 4]])'
        )
    
    X = np.asarray(X)
    
    if X.ndim != 2:
        raise ValueError(
            f'X must be 2D (samples × features), got shape {X.shape}.\n'
            f'If you have 1D data: X = X.reshape(-1, 1)'
        )
    
    n_samples, n_features = X.shape
    
    if n_samples == 0:
        raise ValueError('X has no samples (empty)')
    
    if n_features == 0:
        raise ValueError('X has no features')
    
    # Check y if provided
    if y is not None:
        y = np.asarray(y)
        if len(y) != n_samples:
            raise ValueError(
                f'X and y have inconsistent lengths: {n_samples} vs {len(y)}\n'
                f'Every sample in X needs a label in y'
            )
    
    return X, y
```

### Pattern 3: TensorFlow Eager Execution Errors

```python
# TensorFlow's approach: trace back through computation graph

def run_with_gradient_tape(model, X, y, loss_fn):
    """
    TensorFlow's gradient computation with clear error handling.
    
    TensorFlow philosophy:
    - Track which operations are differentiable
    - Warn if variables not watched
    - Suggest device placement
    """
    import tensorflow as tf
    
    try:
        with tf.GradientTape() as tape:
            logits = model(X, training=True)
            loss = loss_fn(y, logits)
        
        gradients = tape.gradient(loss, model.trainable_variables)
    
    except tf.errors.InvalidArgumentError as e:
        raise ValueError(
            f'Invalid tensor operation.\n'
            f'Common causes:\n'
            f'  1. Shape mismatch: logits shape doesn\'t match y\n'
            f'  2. Type mismatch: y should be same dtype as logits\n'
            f'  3. Device mismatch: X and model on different devices\n'
            f'Error: {e}'
        ) from e
    
    except RuntimeError as e:
        if 'is not being watched' in str(e):
            raise RuntimeError(
                f'Variable not being tracked by GradientTape.\n'
                f'This means the variable was created outside the tape\'s context.\n'
                f'Fix: Create variables inside the `with tf.GradientTape():` block'
            ) from e
        raise
    
    # Check for NaN/Inf in gradients (common bug)
    if any(tf.reduce_any(tf.math.is_nan(g)) for g in gradients if g is not None):
        raise RuntimeError(
            'Gradients are NaN. This usually means:\n'
            '  1. Learning rate too high (exploding gradients)\n'
            '  2. Numerical instability in loss function\n'
            '  3. Bad initialization\n'
            'Try: reduce learning rate, use gradient clipping, or check inputs'
        )
    
    return loss, gradients
```

---

## Gotchas & Anti-Patterns

### Gotcha 1: Jupyter Cell Execution Order

```python
# ❌ BAD: Assumes cells run in written order
# Cell 1
x = 10

# Cell 5 (should depend on Cell 1)
print(x + 5)  # 15

# But if Cell 5 runs before Cell 1, x is undefined!
# This is a hidden state bug specific to Jupyter.

# ✓ GOOD: Make dependencies explicit
# Cell 1
GLOBAL_CONFIG = {
    'x': 10,
    'debug': True
}

# Cell 5
print(GLOBAL_CONFIG['x'] + 5)

# Even better: use "Kernel → Restart Kernel and Run All Cells" 
# to prove the notebook runs top-to-bottom
```

### Gotcha 2: Silent Exceptions in List Comprehensions

```python
# ❌ BAD: Exceptions silently skipped
results = [process(item) for item in items]  # If process() raises, you don't know

# ✓ GOOD: Explicit error handling
results = []
for item in items:
    try:
        results.append(process(item))
    except Exception as e:
        print(f'Failed to process {item}: {e}')
        # Decide: skip item or raise

# Or: use helper function that makes errors visible
def process_safe(item):
    try:
        return process(item)
    except Exception as e:
        raise ProcessError(f'Failed to process {item}') from e

results = [process_safe(item) for item in items]
```

### Gotcha 3: GPU Memory Leaks

```python
# ❌ BAD: Models accumulate in GPU memory
def train_models():
    for epoch in range(100):
        model = create_model()  # GPU memory used
        # model not deleted, stays in memory

# ✓ GOOD: Explicit cleanup
def train_models():
    for epoch in range(100):
        model = create_model()
        # ... training ...
        del model
        torch.cuda.empty_cache()  # Force cleanup

# ✓ BEST: Use context manager
def train_models():
    for epoch in range(100):
        with gpu_memory_guard('training_model'):
            model = create_model()
            # ... training ...
        # Automatically cleaned up
```

### Gotcha 4: Mutable Default Arguments

```python
# ❌ BAD: Default argument is shared across calls
def append_to_list(item, target=[]):
    target.append(item)
    return target

append_to_list(1)  # [1]
append_to_list(2)  # [1, 2] — NOT [2]! Shared state bug

# ✓ GOOD: Use None and create new list
def append_to_list(item, target=None):
    if target is None:
        target = []
    target.append(item)
    return target

append_to_list(1)  # [1]
append_to_list(2)  # [2]
```

### Gotcha 5: Bare Except Clauses

```python
# ❌ BAD: Catches everything, including KeyboardInterrupt
try:
    response = api_call()
except:  # Catches EVERYTHING
    print('Error')

# ✓ GOOD: Specific exception types
try:
    response = api_call()
except (APIError, TimeoutError) as e:
    print(f'API call failed: {e}')
except KeyboardInterrupt:
    raise  # Let user interrupt!
except Exception as e:
    print(f'Unexpected error: {type(e).__name__}')
    raise
```

### Gotcha 6: Silenced Warnings

```python
# ❌ BAD: Suppressing warnings hides problems
import warnings
warnings.filterwarnings('ignore')  # Never do this in notebooks!

# ✓ GOOD: Address the warning
# If deprecation: update code
# If false positive: suppress specific warning with reason

import warnings

# Suppress ONE specific warning with reason
warnings.filterwarnings(
    'ignore',
    message='.*deprecated.*',
    category=DeprecationWarning,
    module='old_library'
)

# Better: just update the code to use new API
# Warnings are teachers
```

---

## Summary Checklist for Course Materials

### For Instructors

- [ ] Provide error catalog (common failures for your domain)
- [ ] Show students how to read error messages (they skip them!)
- [ ] Include "expected to fail" cells that demonstrate error handling
- [ ] Teach "Restart Kernel and Run All Cells" as the debugging gold standard
- [ ] Provide diagnostic functions (like `diagnose_notebook()`)
- [ ] Test error paths in automated checks

### For Notebook Templates

```python
# Every student notebook should include:

# 1. Setup validation
def validate_notebook_setup():
    """Check that the notebook environment is ready."""
    try:
        load_secret('ANTHROPIC_API_KEY')
        print('✓ API key configured')
    except Exception as e:
        print(f'✗ Setup failed: {e}')
        raise
    
    # ... more validation

# 2. Error handling examples
# Show 2-3 examples that students can adapt

# 3. Failure mode catalog
# "If you see X, it means Y, try Z"

# 4. Debugging help
# Link to M1-L0 notebook, suggest Restart Kernel
```

### For Capstone/Production Code

Once notebooks graduate to `.py` files:

```python
# production_code.py

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 1. Custom exception hierarchy
class ProductionError(Exception):
    """Base error for production code."""

# 2. Input validation at entry points
def main(config_path: str):
    config = load_config(config_path)
    validate_config(config)
    # ...

# 3. Structured logging
logger.info('Starting inference', extra={'model': model_name, 'batch_size': 32})

# 4. Resource cleanup
with model_session(model_name) as session:
    results = session.predict(data)

# 5. Monitoring/alerting hooks
if accuracy < alert_threshold:
    send_alert(f'Accuracy dropped to {accuracy}')
```

---

## Additional Resources

### Reading

- **Python Best Practices:** [Real Python Error Handling](https://realpython.com/python-exceptions/)
- **PyTorch Error Messages:** [PyTorch Docs](https://pytorch.org/docs/stable/)
- **scikit-learn Validation:** [Input Validation](https://scikit-learn.org/stable/modules/classes.html#module-sklearn.utils.validation)
- **TensorFlow Errors:** [TF Error Messages Guide](https://www.tensorflow.org/guide/error_messages)

### Tools

- **Traceback:** Use `traceback.print_exc()` to see full error context
- **Debugger:** `pdb.set_trace()` for interactive debugging in notebooks
- **Logging:** `logging` module for structured error tracking
- **Type Hints:** `from typing import ...` to catch errors before runtime

### Next Steps

1. **Extract this guide to your course materials** as reference documentation
2. **Add domain-specific examples** for your AI tasks (e.g., LLM API errors, data pipeline failures)
3. **Create error scenario cells** in each notebook showing expected failures
4. **Build automated checks** that test error paths (like the `test_error_handling()` function)
5. **Link to this guide in error messages** so students can self-serve when things break

---

## Template Error Message for Notebooks

```python
"""
Error handling template for your notebooks:

When something breaks, your error message should answer:
1. WHAT failed? (be specific)
2. WHY did it fail? (architectural reason)
3. HOW do I fix it? (exact steps)
4. WHERE can I learn more? (link to course material)
"""

class TemplateError(Exception):
    """
    Replace TemplateError with your specific exception.
    """
    
    def __init__(self, what: str, why: str, how: str, learn_more: str = None):
        self.what = what
        self.why = why
        self.how = how
        self.learn_more = learn_more
        
        message = f"""
╔════════════════════════════════════════════════════════════╗
║ ERROR: {what}
╚════════════════════════════════════════════════════════════╝

WHY THIS HAPPENED:
  {why}

HOW TO FIX:
  {how}
"""
        if learn_more:
            message += f"\nLEARN MORE:\n  {learn_more}\n"
        
        super().__init__(message)


# Usage in your notebook
if not api_key:
    raise TemplateError(
        what='API key not found',
        why='The notebook cannot authenticate with the Anthropic API',
        how='1. Click the 🔑 icon in the sidebar\n  2. Add secret "ANTHROPIC_API_KEY"\n  3. Re-run this cell',
        learn_more='See M1-L0-notebooks-for-ai-work.ipynb for details'
    )
```

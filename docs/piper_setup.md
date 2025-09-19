# Piper TTS Setup Guide

## 📦 Installation

### Basic Installation

```bash
pip install piper-tts
```

### GPU Support Installation (Optional)

```bash
# For NVIDIA GPU
pip install onnxruntime-gpu

# Or for Apple Silicon
pip install onnxruntime-silicon
```

## 🔊 Download Voice Models

### Download Persian Model

```bash
python3 -m piper.download_voices fa_IR-amir-medium --data-dir ./models/piper
```

### Download English Model

```bash
python3 -m piper.download_voices en_US-lessac-medium --data-dir ./models/piper
```

### Download Other Models

```bash
# Arabic
python3 -m piper.download_voices ar_SA-hamed-medium --data-dir ./models/piper

# Spanish
python3 -m piper.download_voices es_ES-elvira-medium --data-dir ./models/piper

# French
python3 -m piper.download_voices fr_FR-denis-medium --data-dir ./models/piper
```

## ⚙️ Configuration

### .env File

```bash
# Piper TTS Configuration
PIPER_MODEL_PATH=./models/piper
PIPER_USE_CUDA=false
PIPER_USE_MPS=false
```

### Directory Structure

```
ttskit/
├── models/piper/
│   ├── fa_IR-amir-medium.onnx
│   ├── en_US-lessac-medium.onnx
│   ├── ar_SA-hamed-medium.onnx
│   └── ...
├── .env
└── ...
```

## 🚀 Usage

### Basic Usage

```python
from ttskit import TTS

# Create TTS instance
tts = TTS(default_lang="fa")

# Synthesize text
audio = await tts.synth_async("Hello, this is a test.")
```

### Usage with Custom Settings

```python
from ttskit import TTS, SynthConfig

# Custom settings
config = SynthConfig(
    text="Hello, this is a test.",
    lang="fa",
    engine="piper",
    rate=1.2,  # Speech rate
    output_format="wav"
)

# Synthesize
audio = await tts.synth_async(config)
```

## 🔧 Advanced Configuration

### Enable CUDA

```bash
# In .env file
PIPER_USE_CUDA=true
```

### Enable MPS (Apple Silicon)

```bash
# In .env file
PIPER_USE_MPS=true
```

## 📋 Available Models List

### Persian Models

- `fa_IR-amir-medium` - Medium quality male voice
- `fa_IR-dilara-medium` - Medium quality female voice

### English Models

- `en_US-lessac-medium` - American male voice
- `en_US-jenny-medium` - American female voice
- `en_GB-alan-medium` - British male voice

### Arabic Models

- `ar_SA-hamed-medium` - Arabic male voice

## 🐛 Troubleshooting

### Error "No Piper voices found"

```bash
# Check if models/piper directory exists
ls -la ./models/piper/

# Check .onnx files
ls -la ./models/piper/*.onnx
```

### CUDA Error

```bash
# Check CUDA installation
nvidia-smi

# Reinstall onnxruntime-gpu
pip uninstall onnxruntime
pip install onnxruntime-gpu
```

### Memory Error

```bash
# Reduce number of loaded models
# or use smaller models
```

## 📚 Additional Resources

- [Official Piper TTS Documentation](https://github.com/rhasspy/piper)
- [Complete Models List](https://huggingface.co/rhasspy/piper-voices)
- [API Guide](https://github.com/rhasspy/piper/blob/master/python/README.md)

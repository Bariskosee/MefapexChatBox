# 🤖 Enhanced AI Models Configuration

# Available FREE Hugging Face Models for better conversations:

## 🏆 Recommended Models (ordered by quality):

### 1. **microsoft/DialoGPT-medium** 
- Size: 354M parameters
- Best quality conversations
- Slower loading (~2GB)
- Great for natural responses

### 2. **microsoft/DialoGPT-small** (Current)
- Size: 117M parameters  
- Good balance speed/quality
- Fast loading (~351MB)
- Currently loaded

### 3. **facebook/blenderbot_small-90M**
- Size: 90M parameters
- Optimized for chatbots
- Very fast
- Good context understanding

### 4. **google/flan-t5-small**
- Size: 80M parameters
- Instruction following
- Multilingual support
- Good for Q&A

### 5. **gpt2**
- Size: 124M parameters
- General text generation
- Well-tested
- Good fallback

## 🔄 How to Change Models:

Edit `.env` file:
```env
HUGGINGFACE_MODEL=microsoft/DialoGPT-medium
```

Available options:
- `microsoft/DialoGPT-small` (current - fast)
- `microsoft/DialoGPT-medium` (better quality)
- `facebook/blenderbot_small-90M` (chatbot optimized)
- `google/flan-t5-small` (instruction following)
- `gpt2` (general purpose)

## 💡 Performance Notes:

- **Small models**: Fast loading, good for development
- **Medium models**: Better quality, slower loading
- **Turkish support**: All models work with Turkish via translation
- **Memory usage**: Small ~400MB, Medium ~1.5GB

## 🚀 Next Steps:

To upgrade to medium model:
1. Edit `.env`: `HUGGINGFACE_MODEL=microsoft/DialoGPT-medium`
2. Restart application: `python main.py`
3. Wait for model download (~2GB)
4. Test improved responses!

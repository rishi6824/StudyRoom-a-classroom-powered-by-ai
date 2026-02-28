import os

class Config:
    SECRET_KEY = 'your-secret-key-here-change-this-in-production'
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # API Keys for Question Generation (Multiple providers for reliability)
    # Use environment variables: ROUTER_API_KEY, DEEPSEEK_API_KEY, HUGGINGFACE_API_KEY
    ROUTER_API_KEY = os.getenv('ROUTER_API_KEY', '')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', '')
    HUGGINGFACE_API_URL = 'https://api-inference.huggingface.co/models'
    
    # Models for question generation and predictions
    QUESTION_GENERATION_MODEL = 'mistralai/Mistral-7B-Instruct-v0.2'  # or 'gpt2', 'microsoft/DialoGPT-medium'
    
    # API Endpoints
    ROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'  # OpenRouter API
    DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
    ANSWER_ANALYSIS_MODEL = 'facebook/bart-large-mnli'  # for text classification
    SENTIMENT_MODEL = 'cardiffnlp/twitter-roberta-base-sentiment-latest'  # for answer sentiment
    
    # Models for physical/behavioral analysis
    FACE_EMOTION_MODEL = 'trpakov/vit-face-expression'  # Face emotion detection
    VOICE_EMOTION_MODEL = 'ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition'  # Dedicated speech emotion
    BODY_POSE_MODEL = 'facebook/detr-resnet-50'  # Object detection for posture
    
    # Physical analysis settings
    ENABLE_PHYSICAL_ANALYSIS = True
    ANALYSIS_FRAME_INTERVAL = 3  # Increase interval slightly for better processing
    CONFIDENCE_WEIGHT = 0.5  # Confidence is key
    VOICE_WEIGHT = 0.3
    BODY_LANGUAGE_WEIGHT = 0.2
    
    # Interview settings
    MIN_QUESTIONS = 5
    MAX_QUESTIONS = 10
    DEFAULT_QUESTIONS = 5  # Default number of questions to generate
    QUESTION_TIME_LIMIT = 60  # 1 minute per question
    ANSWER_TIME_LIMIT = 30  # 30 seconds for answering
    
    # Chatbot settings
    CHATBOT_NAME = "Rishi"
    MAX_CHAT_HISTORY = 20
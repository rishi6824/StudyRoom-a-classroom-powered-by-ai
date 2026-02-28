class SpeechRecognitionHandler {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.finalTranscript = '';
        this.interimTranscript = '';
        this.onResultCallback = null;
        this.onEndCallback = null;
        
        this.initializeRecognition();
    }
    
    initializeRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateUI('listening');
            };
            
            this.recognition.onresult = (event) => {
                this.interimTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        this.finalTranscript += transcript + ' ';
                    } else {
                        this.interimTranscript += transcript;
                    }
                }
                
                if (this.onResultCallback) {
                    this.onResultCallback(this.finalTranscript, this.interimTranscript);
                }
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.updateUI('error');
                this.stopListening();
            };
            
            this.recognition.onend = () => {
                this.isListening = false;
                this.updateUI('stopped');
                if (this.onEndCallback) {
                    this.onEndCallback(this.finalTranscript);
                }
            };
        } else {
            console.warn('Speech recognition not supported in this browser');
        }
    }
    
    startListening() {
        if (this.recognition && !this.isListening) {
            this.finalTranscript = '';
            this.interimTranscript = '';
            try {
                this.recognition.start();
            } catch (error) {
                console.error('Error starting speech recognition:', error);
            }
        }
    }
    
    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
    }
    
    updateUI(state) {
        const button = document.getElementById('voiceButton');
        const status = document.getElementById('voiceStatus');
        
        if (!button || !status) return;
        
        switch(state) {
            case 'listening':
                button.innerHTML = '🛑 Stop Listening';
                button.classList.add('listening');
                status.textContent = 'Listening... Speak now';
                status.className = 'voice-status listening';
                break;
            case 'stopped':
                button.innerHTML = '🎤 Start Voice Answer';
                button.classList.remove('listening');
                status.textContent = 'Voice input ready';
                status.className = 'voice-status ready';
                break;
            case 'error':
                button.innerHTML = '🎤 Start Voice Answer';
                button.classList.remove('listening');
                status.textContent = 'Voice input error - try again';
                status.className = 'voice-status error';
                break;
        }
    }
    
    setOnResultCallback(callback) {
        this.onResultCallback = callback;
    }
    
    setOnEndCallback(callback) {
        this.onEndCallback = callback;
    }
}



// Global instance
const speechHandler = new SpeechRecognitionHandler();


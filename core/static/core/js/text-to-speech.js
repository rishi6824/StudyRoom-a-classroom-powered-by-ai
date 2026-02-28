// Text-to-Speech Handler
class TextToSpeech {
    constructor() {
        this.synthesis = window.speechSynthesis;
        this.utterance = null;
        this.isSpeaking = false;
        this.isMuted = false;
        this.voices = [];
        this.selectedVoice = null;

        this.loadVoices();
        this.setupEventListeners();
    }

    loadVoices() {
        // Load available voices
        this.voices = this.synthesis.getVoices();

        // Prefer a natural-sounding English voice
        this.selectedVoice = this.voices.find(voice =>
            voice.lang.includes('en') &&
            (voice.name.includes('Google') || voice.name.includes('Natural') || voice.name.includes('Samantha'))
        ) || this.voices.find(voice => voice.lang.includes('en')) || this.voices[0];

        // If voices aren't loaded yet, wait for them
        if (this.voices.length === 0) {
            this.synthesis.onvoiceschanged = () => {
                this.voices = this.synthesis.getVoices();
                this.selectedVoice = this.voices.find(voice => voice.lang.includes('en')) || this.voices[0];
            };
        }
    }

    setupEventListeners() {
        // Handle speech events
        this.synthesis.addEventListener('voiceschanged', () => {
            this.voices = this.synthesis.getVoices();
        });
    }

    speakQuestion(text) {
        return new Promise((resolve, reject) => {
            if (this.isMuted) {
                resolve(); // Resolve immediately if muted
                return;
            }

            // Stop any current speech
            this.stop();

            // Create new utterance
            this.utterance = new SpeechSynthesisUtterance(text);

            // Configure voice
            if (this.selectedVoice) {
                this.utterance.voice = this.selectedVoice;
            }

            // Configure speech properties for interview context
            this.utterance.rate = 0.9;    // Slightly slower for clarity
            this.utterance.pitch = 1.0;   // Normal pitch
            this.utterance.volume = 1.0;  // Full volume

            // Add slight pause for question number
            if (text.startsWith('Question')) {
                this.utterance.rate = 0.85;
            }

            // Event handlers
            this.utterance.onstart = () => {
                this.isSpeaking = true;
                this.updateAISpeakingUI(true);
            };

            this.utterance.onend = () => {
                this.isSpeaking = false;
                this.updateAISpeakingUI(false);
                resolve();
            };

            this.utterance.onerror = (event) => {
                this.isSpeaking = false;
                this.updateAISpeakingUI(false);
                reject(event.error);
            };

            // Start speaking
            if (this.utterance instanceof SpeechSynthesisUtterance) {
                this.synthesis.speak(this.utterance);
            } else {
                console.error('❌ Failed to create valid SpeechSynthesisUtterance');
                this.isSpeaking = false;
                this.updateAISpeakingUI(false);
                resolve();
            }
        });
    }

    updateAISpeakingUI(speaking) {
        const aiSpeakingIndicator = document.getElementById('aiSpeakingIndicator');
        const statusText = document.getElementById('statusText');
        const speechBubble = document.getElementById('aiSpeechBubble');

        if (speaking) {
            if (aiSpeakingIndicator) aiSpeakingIndicator.style.display = 'flex';
            if (statusText) statusText.textContent = 'AI is Asking Question';
            if (speechBubble) speechBubble.classList.add('speaking');
        } else {
            if (speechBubble) speechBubble.classList.remove('speaking');
            // Keep indicator visible for a moment after speaking
            setTimeout(() => {
                if (aiSpeakingIndicator) aiSpeakingIndicator.style.display = 'none';
            }, 1000);
        }
    }

    stop() {
        if (this.synthesis.speaking) {
            this.synthesis.cancel();
            this.isSpeaking = false;
            this.updateAISpeakingUI(false);
        }
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        if (this.isMuted) {
            this.stop();
        }
        return this.isMuted;
    }

    setVoice(voiceName) {
        this.selectedVoice = this.voices.find(voice => voice.name === voiceName) || this.selectedVoice;
    }

    getAvailableVoices() {
        return this.voices.filter(voice => voice.lang.includes('en'));
    }
}

// Global instance
// const textToSpeech = new TextToSpeech(); // Already instantiated in HTML
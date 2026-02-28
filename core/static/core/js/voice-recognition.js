// Voice Recognition Handler
class VoiceRecognition {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.audioContext = null;
        this.analyser = null;
        this.mediaStreamSource = null;
        this.animationId = null;
        this.onResultCallback = null;
        this.autoStopTimeout = null;
        this.mediaStream = null;
        
        // Check browser support first
        if (this.isSpeechRecognitionSupported()) {
            this.initializeRecognition();
            this.setupEventListeners();
        } else {
            this.showUnsupportedMessage();
        }
    }
    
    // Setup event listeners for UI elements
    setupEventListeners() {
        document.addEventListener('DOMContentLoaded', () => {
            const voiceButton = document.getElementById('voiceButton');
            const stopButton = document.getElementById('stopVoiceButton');
            
            if (voiceButton) {
                voiceButton.addEventListener('click', () => this.startListeningWithPermission());
            }
            
            if (stopButton) {
                stopButton.addEventListener('click', () => this.stopListening());
            }
        });
    }
    
    // Check if browser supports speech recognition
    isSpeechRecognitionSupported() {
        return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
    }
    
    // Show message for unsupported browsers
    showUnsupportedMessage() {
        console.warn('Speech recognition not supported in this browser');
        document.addEventListener('DOMContentLoaded', () => {
            const voiceSection = document.querySelector('.voice-section');
            if (voiceSection) {
                voiceSection.innerHTML = `
                    <div style="text-align: center; padding: 1rem; color: #666;">
                        <p>⚠️ Voice input is not supported in your browser.</p>
                        <p>Please use Chrome, Edge, or Safari for voice features.</p>
                        <p>You can still type your answers below.</p>
                    </div>
                `;
            }
        });
    }
    
    initializeRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Configuration
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        this.recognition.maxAlternatives = 1;
        
        // Event Handlers
        this.recognition.onstart = () => {
            this.isListening = true;
            console.log('🎤 Voice recognition started');
            this.updateUI('listening');
        };
        
        this.recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Update the textarea with the recognized speech
            this.updateAnswerText(finalTranscript || interimTranscript);
        };
        
        this.recognition.onerror = (event) => {
            console.error('❌ Speech recognition error:', event.error);
            
            // Handle permission denied error specifically
            if (event.error === 'not-allowed') {
                this.handlePermissionDenied();
            }
            
            this.stopListening();
            this.updateUI('error');
        };
        
        this.recognition.onend = () => {
            this.isListening = false;
            console.log('🛑 Voice recognition ended');
            this.updateUI('stopped');
            
            // Clean up media stream
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => track.stop());
                this.mediaStream = null;
            }
        };
    }
    
    // Handle permission denied error
    handlePermissionDenied() {
        console.error('Microphone permission denied');
        this.updateUI('permission_denied');
        
        // Show user-friendly message
        document.addEventListener('DOMContentLoaded', () => {
            const status = document.getElementById('voiceStatus');
            if (status) {
                status.innerHTML = '❌ Microphone access denied. <a href="#" onclick="voiceRecognition.showPermissionHelp()">Click here for help</a>';
                status.className = 'voice-status error';
            }
        });
    }
    
    // Show help for permission issues
    showPermissionHelp() {
        const helpMessage = `
            <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 1rem; margin: 1rem 0; border-radius: 4px;">
                <h4>🔒 Microphone Permission Help</h4>
                <p><strong>To enable microphone access:</strong></p>
                <ol>
                    <li>Look for the microphone permission prompt in your browser's address bar</li>
                    <li>Click "Allow" to grant microphone access</li>
                    <li>If you previously denied access, click the lock icon 🔒 in the address bar and change the permission to "Allow"</li>
                    <li>Refresh the page and try again</li>
                </ol>
                <p><strong>Browser-specific instructions:</strong></p>
                <ul>
                    <li><strong>Chrome:</strong> Lock icon → Site settings → Microphone → Allow</li>
                    <li><strong>Firefox:</strong> Camera icon → Allow microphone access</li>
                    <li><strong>Safari:</strong> Preferences → Websites → Microphone → Allow</li>
                </ul>
            </div>
        `;
        
        // Insert help message near the voice section
        const voiceSection = document.querySelector('.voice-section');
        if (voiceSection) {
            const existingHelp = voiceSection.querySelector('.permission-help');
            if (!existingHelp) {
                const helpDiv = document.createElement('div');
                helpDiv.className = 'permission-help';
                helpDiv.innerHTML = helpMessage;
                voiceSection.appendChild(helpDiv);
            }
        }
    }
    
    // Request microphone permission and start listening
    async startListeningWithPermission() {
        try {
            // First request microphone permission
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                },
                video: false 
            });
            
            // Permission granted, start recognition
            console.log('✅ Microphone permission granted');
            this.startListening();
            
        } catch (error) {
            console.error('❌ Error accessing microphone:', error);
            
            if (error.name === 'NotAllowedError') {
                this.handlePermissionDenied();
            } else if (error.name === 'NotFoundError') {
                this.updateUI('no_microphone');
            } else {
                this.updateUI('error');
            }
        }
    }
    
    // Update the answer textarea with recognized speech
    updateAnswerText(transcript) {
        const answerTextarea = document.getElementById('answer');
        const voicePreview = document.getElementById('voicePreview');
        
        if (answerTextarea) {
            answerTextarea.value = transcript;
            // Trigger input event for any listeners
            answerTextarea.dispatchEvent(new Event('input', { bubbles: true }));
        }
        
        if (voicePreview) {
            voicePreview.textContent = transcript;
            voicePreview.style.display = transcript ? 'block' : 'none';
        }
        
        // Call the callback if provided
        if (this.onResultCallback) {
            this.onResultCallback(transcript);
        }
    }
    
    // Update UI based on voice recognition state
    updateUI(state) {
        const voiceButton = document.getElementById('voiceButton');
        const stopButton = document.getElementById('stopVoiceButton');
        const status = document.getElementById('voiceStatus');
        const visualizer = document.getElementById('visualizer');
        const recordingIndicator = document.getElementById('recordingIndicator');

        if (!voiceButton || !stopButton || !status) return;

        switch(state) {
            case 'listening':
                voiceButton.style.display = 'none';
                stopButton.style.display = 'inline-block';
                status.textContent = '🎤 Listening... Speak now';
                status.className = 'voice-status listening';
                if (visualizer) visualizer.style.display = 'block';
                if (recordingIndicator) recordingIndicator.style.display = 'block';
                break;
                
            case 'stopped':
                voiceButton.style.display = 'inline-block';
                stopButton.style.display = 'none';
                status.textContent = '✅ Ready to speak';
                status.className = 'voice-status ready';
                if (visualizer) visualizer.style.display = 'none';
                if (recordingIndicator) recordingIndicator.style.display = 'none';
                break;
                
            case 'error':
                voiceButton.style.display = 'inline-block';
                stopButton.style.display = 'none';
                status.textContent = '❌ Voice input error - try again';
                status.className = 'voice-status error';
                if (visualizer) visualizer.style.display = 'none';
                if (recordingIndicator) recordingIndicator.style.display = 'none';
                break;
                
            case 'permission_denied':
                voiceButton.style.display = 'inline-block';
                stopButton.style.display = 'none';
                status.innerHTML = '❌ Microphone access denied. <a href="#" style="color: #007bff; text-decoration: underline;" onclick="voiceRecognition.showPermissionHelp()">Click here for help</a>';
                status.className = 'voice-status error';
                if (visualizer) visualizer.style.display = 'none';
                if (recordingIndicator) recordingIndicator.style.display = 'none';
                break;
                
            case 'no_microphone':
                voiceButton.style.display = 'inline-block';
                stopButton.style.display = 'none';
                status.textContent = '❌ No microphone detected';
                status.className = 'voice-status error';
                if (visualizer) visualizer.style.display = 'none';
                if (recordingIndicator) recordingIndicator.style.display = 'none';
                break;
        }
    }
    
    initialize(stream) {
        if (!stream) {
            console.warn('No audio stream available for voice recognition');
            return;
        }
        this.setupAudioVisualization(stream);
    }
    
    setupAudioVisualization(stream) {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.mediaStreamSource = this.audioContext.createMediaStreamSource(stream);
            
            this.analyser.fftSize = 256;
            this.mediaStreamSource.connect(this.analyser);
            
            this.setupVisualizer();
        } catch (e) {
            console.log('Audio visualization not supported:', e);
        }
    }
    
    setupVisualizer() {
        const canvas = document.getElementById('visualizer');
        if (!canvas) return;
        
        const canvasCtx = canvas.getContext('2d');
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        const draw = () => {
            this.animationId = requestAnimationFrame(draw);
            
            if (!this.isListening) return;
            
            this.analyser.getByteFrequencyData(dataArray);
            
            // Clear canvas
            canvasCtx.fillStyle = 'rgb(0, 0, 0)';
            canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Draw frequency bars
            const barWidth = (canvas.width / bufferLength) * 2.5;
            let x = 0;
            
            for (let i = 0; i < bufferLength; i++) {
                const barHeight = dataArray[i] / 2;
                
                // Create gradient effect based on volume
                const gradient = canvasCtx.createLinearGradient(0, canvas.height - barHeight, 0, canvas.height);
                gradient.addColorStop(0, `rgb(${barHeight + 100}, 50, 50)`);
                gradient.addColorStop(1, `rgb(${barHeight + 50}, 25, 25)`);
                
                canvasCtx.fillStyle = gradient;
                canvasCtx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                
                x += barWidth + 1;
            }
        };
        
        draw();
    }
    
    // Auto-stop after specified time (for 30-second answer limit)
    stopAutomatically(delay = 25000) {
        if (this.autoStopTimeout) {
            clearTimeout(this.autoStopTimeout);
        }
        
        this.autoStopTimeout = setTimeout(() => {
            if (this.isListening) {
                console.log('⏰ Auto-stopping voice recognition');
                this.stopListening();
            }
        }, delay);
    }
    
    startListening() {
        if (!this.recognition) {
            console.error('Speech recognition not initialized');
            this.updateUI('error');
            return;
        }
        
        if (this.isListening) {
            console.log('Already listening');
            return;
        }
        
        try {
            this.recognition.start();
            // Auto-stop after 25 seconds (5 seconds before 30-second limit)
            this.stopAutomatically(25000);
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            this.updateUI('error');
        }
    }
    
    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
        
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        if (this.autoStopTimeout) {
            clearTimeout(this.autoStopTimeout);
        }
        
        // Stop media stream tracks
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        this.updateUI('stopped');
    }
    
    // Set callback for when speech is recognized
    set onResult(callback) {
        this.onResultCallback = callback;
    }
    
    // Clean up resources
    destroy() {
        this.stopListening();
        if (this.audioContext) {
            this.audioContext.close().then(() => {
                console.log('✅ Audio context closed in destroy');
            }).catch(err => {
                console.error('Error closing audio context:', err);
            });
        }
        
        // Clean up media stream source
        if (this.mediaStreamSource) {
            try {
                this.mediaStreamSource.disconnect();
                this.mediaStreamSource = null;
            } catch (e) {
                console.error('Error disconnecting media stream source:', e);
            }
        }
        
        // Clean up analyser
        if (this.analyser) {
            try {
                this.analyser.disconnect();
                this.analyser = null;
            } catch (e) {
                console.error('Error disconnecting analyser:', e);
            }
        }
    }
}

// Global instance
const voiceRecognition = new VoiceRecognition();
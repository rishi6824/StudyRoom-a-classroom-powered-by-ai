class VideoInterview {
    constructor() {
        this.videoElement = null;
        this.canvasElement = null;
        this.ctx = null;
        this.stream = null;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.recordedChunks = [];
    }
    
    async initializeCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { width: 640, height: 480 }, 
                audio: true 
            });
            
            this.videoElement = document.getElementById('interviewVideo');
            if (this.videoElement) {
                this.videoElement.srcObject = this.stream;
            }
            
            return true;
        } catch (error) {
            console.error('Error accessing camera:', error);
            return false;
        }
    }
    
    captureFrame() {
        if (!this.videoElement || !this.stream) return null;
        
        if (!this.canvasElement) {
            this.canvasElement = document.createElement('canvas');
            this.ctx = this.canvasElement.getContext('2d');
        }
        
        this.canvasElement.width = this.videoElement.videoWidth;
        this.canvasElement.height = this.videoElement.videoHeight;
        this.ctx.drawImage(this.videoElement, 0, 0);
        
        return this.canvasElement.toDataURL('image/jpeg', 0.8);
    }
    
    startRecording() {
        if (!this.stream) return;
        
        this.recordedChunks = [];
        this.mediaRecorder = new MediaRecorder(this.stream, { 
            mimeType: 'video/webm; codecs=vp9' 
        });
        
        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.recordedChunks.push(event.data);
            }
        };
        
        this.mediaRecorder.start();
        this.isRecording = true;
    }
    
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            return new Promise((resolve) => {
                this.mediaRecorder.onstop = () => {
                    const blob = new Blob(this.recordedChunks, { type: 'video/webm' });
                    resolve(blob);
                };
            });
        }
        return Promise.resolve(null);
    }
    
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
    }
}

// Global instance
const videoInterview = new VideoInterview();
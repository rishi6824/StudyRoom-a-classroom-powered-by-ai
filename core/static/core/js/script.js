// Utility functions for the interview application

function uploadResume() {
    const fileInput = document.getElementById('resumeUpload');
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select a file first');
        return;
    }

    const formData = new FormData();
    formData.append('resume', file);

    // Get CSRF token from the meta tag or a hidden input if available
    const csrftoken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
        || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    fetch('/resume/upload/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            const resultsDiv = document.getElementById('resumeResults');
            if (data.success) {
                resultsDiv.innerHTML = `
                <div class="upload-success">
                    <h4>Resume Analysis Complete!</h4>
                    <p><strong>Skills Found:</strong> ${data.skills.join(', ')}</p>
                    <p><strong>Preview:</strong> ${data.text_preview}</p>
                </div>
            `;
            } else {
                resultsDiv.innerHTML = `<div class="upload-error">Error: ${data.error}</div>`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('resumeResults').innerHTML =
                '<div class="upload-error">An error occurred during upload</div>';
        });
}

// Interview timer functionality
class InterviewTimer {
    constructor(duration, displayElement) {
        this.duration = duration;
        this.display = displayElement;
        this.timer = null;
        this.remaining = duration;
    }

    start() {
        this.timer = setInterval(() => {
            this.remaining--;
            this.updateDisplay();

            if (this.remaining <= 0) {
                this.stop();
                // Auto-submit when time is up
                document.getElementById('answerForm').dispatchEvent(new Event('submit'));
            }
        }, 1000);
    }

    stop() {
        clearInterval(this.timer);
    }

    updateDisplay() {
        const minutes = Math.floor(this.remaining / 60);
        const seconds = this.remaining % 60;
        this.display.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
}

// Initialize timer if on interview page
document.addEventListener('DOMContentLoaded', function () {
    const timerDisplay = document.getElementById('timer');
    if (timerDisplay) {
        const timer = new InterviewTimer(180, timerDisplay); // 3 minutes
        timer.start();
    }
});

// Chatbot functionality
function initializeChatbot() {
    const chatInput = document.getElementById('userInput');
    if (chatInput) {
        chatInput.focus();
    }
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Utility functions
document.addEventListener('DOMContentLoaded', function () {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});
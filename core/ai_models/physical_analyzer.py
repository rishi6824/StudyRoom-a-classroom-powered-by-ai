"""
Physical Actions Analyzer
Analyzes confidence, voice, body language, and actions during interview using Hugging Face API
"""
import requests
import json
import base64
import numpy as np
from .config import Config

class PhysicalAnalyzer:
    def __init__(self):
        self.api_key = Config.HUGGINGFACE_API_KEY
        self.api_url = Config.HUGGINGFACE_API_URL
        
        # Hugging Face models for analysis
        self.face_emotion_model = 'trpakov/vit-face-expression'  # Face emotion detection
        self.voice_emotion_model = 'j-hartmann/emotion-english-distilroberta-base'  # Voice emotion
        self.sentiment_model = Config.SENTIMENT_MODEL
        self.body_pose_model = 'facebook/detr-resnet-50'  # Body pose detection
        
        # Store analysis results
        self.current_analysis = {
            'confidence': 0.0,
            'voice_quality': 0.0,
            'body_language': 0.0,
            'overall_physical_score': 0.0,
            'details': {}
        }
    
    def analyze_video_frame(self, frame_data):
        """
        Analyze a video frame for facial expressions and body language
        frame_data: base64 encoded image or image array
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Prepare image data
            if isinstance(frame_data, str):
                # Base64 encoded string (already base64)
                image_data = frame_data
            else:
                # If numpy array or other format, convert to base64
                # For now, assume string is base64
                image_data = str(frame_data)
            
            # Analyze face emotions
            emotion_scores = self._analyze_face_emotion(image_data, headers)
            
            # Analyze objects (person counting and phone detection)
            object_results = self._analyze_objects(image_data, headers)
            
            # Calculate confidence based on facial expressions
            confidence = self._calculate_confidence(emotion_scores)
            
            return {
                'emotions': emotion_scores,
                'posture_score': object_results.get('posture_score', 5.0),
                'confidence': confidence,
                'person_count': object_results.get('person_count', 0),
                'phone_detected': object_results.get('phone_detected', False)
            }
            
        except Exception as e:
            print(f"Error analyzing video frame: {e}")
            return None

    def _analyze_face_emotion(self, image_data, headers):
        """Analyze facial emotions using Hugging Face model"""
        try:
            payload = {"inputs": f"data:image/jpeg;base64,{image_data}"}
            api_endpoint = f"https://api-inference.huggingface.co/models/{self.face_emotion_model}"
            
            response = requests.post(api_endpoint, headers=headers, json=payload, timeout=12)
            
            if response.status_code == 200:
                result = response.json()
                # trpakov/vit-face-expression returns list of dicts with label and score
                if isinstance(result, list):
                    emotions = {item['label'].lower(): item['score'] for item in result}
                    return emotions
            else:
                print(f"Face API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error in face emotion analysis: {e}")
        return {}

    def _analyze_objects(self, image_data, headers):
        """Detect persons and cell phones in the frame"""
        try:
            payload = {"inputs": f"data:image/jpeg;base64,{image_data}"}
            api_endpoint = f"https://api-inference.huggingface.co/models/{self.body_pose_model}"
            
            response = requests.post(api_endpoint, headers=headers, json=payload, timeout=12)
            
            if response.status_code == 200:
                result = response.json()
                
                posture_score = 6.0 # Base neutral
                person_count = 0
                phone_detected = False
                
                if isinstance(result, list):
                    # Count persons
                    persons = [item for item in result if 'person' in item.get('label', '').lower()]
                    person_count = len(persons)
                    
                    # Detect mobile phones
                    phones = [item for item in result if 'phone' in item.get('label', '').lower()]
                    if phones:
                        phone_detected = True
                    
                    if persons:
                        # Clear person detected = better posture score
                        posture_score += 2.0
                        
                        # Tracking movement if we have previous box (simple heuristic)
                        box = persons[0].get('box', {})
                        if hasattr(self, '_prev_box') and box:
                            # Calculate movement (simplified)
                            diff = abs(box.get('xmin', 0) - self._prev_box.get('xmin', 0)) + \
                                   abs(box.get('ymin', 0) - self._prev_box.get('ymin', 0))
                            
                            # Excessive movement might indicate fidgeting/nervousness
                            if diff > 50: posture_score -= 1.5
                            elif diff < 10: posture_score += 1.0 # Stable is good
                        
                        self._prev_box = box
                    else:
                        posture_score = 4.0 # Person not clearly in frame
                    
                    # Penalize if more than one person detected
                    if person_count > 1:
                        posture_score -= 3.0
                    
                    # Heavily penalize if phone detected
                    if phone_detected:
                        posture_score -= 4.0
                
                return {
                    'posture_score': min(10.0, max(0.0, posture_score)),
                    'person_count': person_count,
                    'phone_detected': phone_detected
                }
        except Exception as e:
            print(f"Error in object analysis: {e}")
        return {'posture_score': 5.0, 'person_count': 1, 'phone_detected': False}

    def _analyze_body_posture(self, image_data, headers):
        """Deprecated: use _analyze_objects instead"""
        res = self._analyze_objects(image_data, headers)
        return res.get('posture_score', 5.0)

    def _calculate_confidence(self, emotion_scores):
        """Refined confidence calculation for interview context"""
        try:
            if not emotion_scores:
                return 5.0
            
            # Labels for vit-face-expression: [neutral, happy, sad, surprise, fear, disgust, angry]
            # In an interview, neutral and happy are high confidence indicators.
            # Surprise/Fear/Sad/Angry are low confidence indicators.
            
            conf_level = emotion_scores.get('neutral', 0.5) * 8.0 + \
                         emotion_scores.get('happy', 0) * 10.0 - \
                         emotion_scores.get('fear', 0) * 6.0 - \
                         emotion_scores.get('sad', 0) * 4.0 - \
                         emotion_scores.get('angry', 0) * 5.0
            
            # Normalize to 0-10
            return min(10.0, max(0.0, conf_level))
        except Exception as e:
            return 5.0

    def _analyze_voice_emotion(self, audio_data, headers):
        """Analyze actual voice emotion using speech model"""
        try:
            # Accuracy improvement: Send binary audio if available
            # If string, assume it's base64 from the frontend
            if isinstance(audio_data, str) and len(audio_data) > 100:
                # Remove header if present
                if ',' in audio_data:
                    audio_data = audio_data.split(',')[1]
                payload = base64.b64decode(audio_data)
            else:
                payload = audio_data

            api_endpoint = f"https://api-inference.huggingface.co/models/{self.voice_emotion_model}"
            
            # Send binary data directly for audio models
            response = requests.post(
                api_endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                data=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                # wav2vec2-lg-xlsr-en-speech-emotion-recognition returns list of dicts
                if isinstance(result, list):
                    emotions = {item['label'].lower(): item['score'] for item in result}
                    return emotions
            else:
                print(f"Voice API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error in voice emotion analysis: {e}")
        return {}

    def analyze_audio(self, audio_data):
        """Analyze audio for voice confidence and quality"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Analyze voice emotion
            emotion_data = self._analyze_voice_emotion(audio_data, headers)
            
            # Calculate voice score based on confidence in speech
            voice_score = self._analyze_speech_quality(audio_data, emotion_data)
            
            return {
                'emotions': emotion_data,
                'voice_score': voice_score
            }
        except Exception as e:
            print(f"Error analyzing audio: {e}")
            return {'emotions': {}, 'voice_score': 5.0}

    def _analyze_speech_quality(self, audio_data, emotion_data):
        """Improved speech quality analysis using emotion labels"""
        if not emotion_data: return 5.0
        
        # High confidence in speech: calm, happy, pleasant
        # Low confidence: angry, fearful, sad
        positive = emotion_data.get('calm', 0) + emotion_data.get('happy', 0) + emotion_data.get('neutral', 0)
        negative = emotion_data.get('angry', 0) + emotion_data.get('fear', 0) + emotion_data.get('sad', 0)
        
        quality = 5.0 + (positive * 5.0) - (negative * 3.0)
        return min(10.0, max(0.0, quality))

    def analyze_realtime_data(self, video_frames, audio_segments):
        """Analyze data with weights from Config"""
        try:
            results = []
            
            # Video analysis
            conf_scores = []
            posture_scores = []
            person_counts = []
            phone_detected_flags = []
            
            for frame in video_frames:
                fa = self.analyze_video_frame(frame)
                if fa:
                    conf_scores.append(fa.get('confidence', 5.0))
                    posture_scores.append(fa.get('posture_score', 5.0))
                    person_counts.append(fa.get('person_count', 1))
                    phone_detected_flags.append(fa.get('phone_detected', False))
            
            # Audio analysis
            voice_scores = []
            for audio in audio_segments:
                aa = self.analyze_audio(audio)
                if aa:
                    voice_scores.append(aa.get('voice_score', 5.0))
            
            # Calculate final results
            avg_conf = np.mean(conf_scores) if conf_scores else self.current_analysis['confidence']
            avg_posture = np.mean(posture_scores) if posture_scores else self.current_analysis['body_language']
            avg_voice = np.mean(voice_scores) if voice_scores else self.current_analysis['voice_quality']
            
            max_person_count = max(person_counts) if person_counts else 1
            any_phone_detected = any(phone_detected_flags) if phone_detected_flags else False
            
            # Apply weighted score
            overall = (avg_conf * Config.CONFIDENCE_WEIGHT + 
                       avg_voice * Config.VOICE_WEIGHT + 
                       avg_posture * Config.BODY_LANGUAGE_WEIGHT)
            
            # Additional security violations check
            violations = []
            if any_phone_detected:
                violations.append("Mobile phone detected")
            
            if max_person_count == 0:
                violations.append("No face detected")
            elif max_person_count > 1:
                violations.append(f"Multiple people detected ({max_person_count})")
            
            self.current_analysis = {
                'confidence': round(float(avg_conf), 2),
                'voice_quality': round(float(avg_voice), 2),
                'body_language': round(float(avg_posture), 2),
                'overall_physical_score': round(float(overall), 2),
                'person_count': max_person_count,
                'phone_detected': any_phone_detected,
                'violations': violations,
                'details': {
                    'confidence_history': conf_scores,
                    'voice_history': voice_scores,
                    'posture_history': posture_scores,
                    'person_counts': person_counts,
                    'phone_detections': phone_detected_flags
                }
            }
            return self.current_analysis
        except Exception as e:
            print(f"Error in realtime analysis: {e}")
            import traceback
            traceback.print_exc()
            return self.current_analysis
    
    def get_analysis_summary(self):
        """Get current analysis summary"""
        return {
            'confidence': self.current_analysis.get('confidence', 0.0),
            'voice_quality': self.current_analysis.get('voice_quality', 0.0),
            'body_language': self.current_analysis.get('body_language', 0.0),
            'overall_physical_score': self.current_analysis.get('overall_physical_score', 0.0)
        }
    
    def reset_analysis(self):
        """Reset analysis for new question"""
        self.current_analysis = {
            'confidence': 0.0,
            'voice_quality': 0.0,
            'body_language': 0.0,
            'overall_physical_score': 0.0,
            'details': {}
        }

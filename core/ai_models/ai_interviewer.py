import json
import os
import nltk
import requests
from nltk.tokenize import word_tokenize, sent_tokenize
from .config import Config

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class AIInterviewer:
    def __init__(self):
        self.questions_file = os.path.join(os.path.dirname(__file__), 'data', 'questions', 'interview_questions.json')
        self.questions = self._load_questions()
        self.hf_api_key = Config.HUGGINGFACE_API_KEY
        self.hf_api_url = Config.HUGGINGFACE_API_URL
        self.sentiment_model = Config.SENTIMENT_MODEL
        self.analysis_model = Config.ANSWER_ANALYSIS_MODEL
        
        # Additional API keys
        self.router_api_key = Config.ROUTER_API_KEY
        self.deepseek_api_key = Config.DEEPSEEK_API_KEY
        self.router_api_url = Config.ROUTER_API_URL
        self.deepseek_api_url = Config.DEEPSEEK_API_URL
    
    def _load_questions(self):
        try:
            with open(self.questions_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Questions file {self.questions_file} not found. Using default questions.")
            return self._get_default_questions()
    
    def _get_default_questions(self):
        return {
            "software_engineer": [
                {
                    "question": "Can you explain object-oriented programming and its main principles?",
                    "type": "technical",
                    "keywords": ["encapsulation", "inheritance", "polymorphism", "abstraction", "classes", "objects"]
                },
                {
                    "question": "Describe a challenging technical problem you solved and how you approached it.",
                    "type": "behavioral",
                    "keywords": ["problem", "solution", "approach", "challenge", "result", "learning"]
                },
                {
                    "question": "How do you ensure code quality and what testing methodologies do you use?",
                    "type": "technical",
                    "keywords": ["testing", "quality", "unit tests", "integration", "code review", "best practices"]
                }
            ],
            "data_scientist": [
                {
                    "question": "Explain the difference between supervised and unsupervised learning.",
                    "type": "technical",
                    "keywords": ["supervised", "unsupervised", "labeled data", "clustering", "classification", "training"]
                },
                {
                    "question": "How do you handle missing data in a dataset?",
                    "type": "technical",
                    "keywords": ["missing data", "imputation", "removal", "analysis", "strategy", "impact"]
                }
            ]
        }
    
    def get_questions(self, job_role):
        return self.questions.get(job_role, self.questions['software_engineer'])
    
    def analyze_answer(self, job_role, question_index, answer, resume_analysis=None):
        questions = self.get_questions(job_role)
        
        if question_index >= len(questions):
            return 0, "Invalid question index", {}
        
        question = questions[question_index]
        
        # Try Router API first for advanced analysis
        router_score, router_feedback, router_analysis = self._analyze_with_router_api(
            question.get('question', ''),
            answer,
            question.get('keywords', [])
        )
        
        if router_score is not None:
            print(f"✅ Analyzed answer using Router API: {router_score}")
            analysis = {
                'word_count': len(word_tokenize(answer)),
                'sentences': len(sent_tokenize(answer)),
                'router_analysis': router_analysis if router_analysis else {}
            }
            return router_score, router_feedback, analysis
        
        # Try DeepSeek API second
        deepseek_score, deepseek_feedback, deepseek_analysis = self._analyze_with_deepseek_api(
            question.get('question', ''),
            answer,
            question.get('keywords', [])
        )
        
        if deepseek_score is not None:
            print(f"✅ Analyzed answer using DeepSeek API: {deepseek_score}")
            analysis = {
                'word_count': len(word_tokenize(answer)),
                'sentences': len(sent_tokenize(answer)),
                'deepseek_analysis': deepseek_analysis if deepseek_analysis else {}
            }
            return deepseek_score, deepseek_feedback, analysis
        
        # Try Hugging Face API third
        hf_score, hf_feedback, hf_analysis = self._analyze_with_hf_api(
            question.get('question', ''),
            answer,
            question.get('keywords', [])
        )
        
        if hf_score is not None:
            print(f"✅ Analyzed answer using Hugging Face API: {hf_score}")
            analysis = {
                'word_count': len(word_tokenize(answer)),
                'sentences': len(sent_tokenize(answer)),
                'hf_analysis': hf_analysis if hf_analysis else {}
            }
            return hf_score, hf_feedback, analysis
        
        # Basic analysis (fallback)
        basic_score = self._calculate_score(answer, question.get('keywords', []))
        basic_feedback = self._generate_feedback(answer, question.get('keywords', []), basic_score)
        
        print(f"⚠️ All APIs failed, using basic analysis: {basic_score}")
        
        analysis = {
            'word_count': len(word_tokenize(answer)),
            'sentences': len(sent_tokenize(answer)),
            'basic_analysis': True
        }
        
        return basic_score, basic_feedback, analysis
    
    def _calculate_score(self, answer, expected_keywords):
        if not answer.strip():
            return 0
        
        answer_lower = answer.lower()
        keywords_found = 0
        
        for keyword in expected_keywords:
            if keyword.lower() in answer_lower:
                keywords_found += 1
        
        # Calculate score based on keyword matches and answer length
        keyword_score = (keywords_found / len(expected_keywords)) * 6 if expected_keywords else 0
        
        # Length score (encourage detailed answers)
        word_count = len(word_tokenize(answer))
        length_score = min(4, word_count / 25)  # Max 4 points for length
        
        total_score = min(10, keyword_score + length_score)
        return round(total_score, 1)
    
    def _generate_feedback(self, answer, expected_keywords, score):
        if score >= 8:
            return "Excellent answer! You covered the key points clearly and thoroughly."
        elif score >= 6:
            return "Good answer. You mentioned some relevant points but could add more detail."
        elif score >= 4:
            return "Average answer. Consider providing more specific examples and details."
        else:
            missing_keywords = [kw for kw in expected_keywords if kw.lower() not in answer.lower()]
            if missing_keywords:
                return f"Try to include concepts like: {', '.join(missing_keywords[:3])}"
            else:
                return "Please provide a more detailed and structured answer."
    
    def _analyze_with_hf_api(self, question, answer, expected_keywords):
        """Analyze answer using Hugging Face models for sentiment and classification"""
        try:
            headers = {
                "Authorization": f"Bearer {self.hf_api_key}",
                "Content-Type": "application/json"
            }
            
            # 1. Sentiment Analysis
            sentiment_score = None
            sentiment_label = None
            try:
                sentiment_payload = {
                    "inputs": answer,
                }
                sentiment_api_endpoint = f"https://api-inference.huggingface.co/models/{self.sentiment_model}"
                sentiment_response = requests.post(
                    sentiment_api_endpoint,
                    headers=headers,
                    json=sentiment_payload,
                    timeout=15
                )
                
                if sentiment_response.status_code == 200:
                    sentiment_result = sentiment_response.json()
                    if isinstance(sentiment_result, list):
                        sentiment_result = sentiment_result[0]
                    
                    # Extract sentiment label and score
                    if isinstance(sentiment_result, list):
                        # Sort by score (highest first)
                        sentiment_result = sorted(sentiment_result, key=lambda x: x.get('score', 0), reverse=True)
                        sentiment_label = sentiment_result[0].get('label', 'neutral')
                        sentiment_score = sentiment_result[0].get('score', 0.5)
            except Exception as e:
                print(f"Sentiment analysis error: {e}")
            
            # 2. Text Classification (answer quality)
            quality_score = None
            try:
                # Use zero-shot classification to evaluate answer quality
                classification_payload = {
                    "inputs": answer,
                    "parameters": {
                        "candidate_labels": ["excellent", "good", "average", "poor"],
                        "multi_label": False
                    }
                }
                
                # Try using sentence similarity or text classification
                # For better results, use models like facebook/bart-large-mnli
                if '/mnli' in self.analysis_model or '/bart' in self.analysis_model:
                    # Zero-shot classification
                    analysis_api_endpoint = f"https://api-inference.huggingface.co/models/{self.analysis_model}"
                    classification_response = requests.post(
                        analysis_api_endpoint,
                        headers=headers,
                        json=classification_payload,
                        timeout=15
                    )
                    
                    if classification_response.status_code == 200:
                        quality_result = classification_response.json()
                        if isinstance(quality_result, list):
                            quality_result = quality_result[0]
                        
                        # Map quality labels to scores
                        quality_map = {
                            "excellent": 9.0,
                            "good": 7.0,
                            "average": 5.0,
                            "poor": 3.0
                        }
                        
                        if isinstance(quality_result, list):
                            quality_result = quality_result[0]
                        
                        quality_label = quality_result.get('label', 'average')
                        quality_score = quality_result.get('score', 0.5)
                        
                        # Calculate weighted score
                        base_score = quality_map.get(quality_label.lower(), 5.0)
                        quality_score = base_score * quality_result.get('score', 0.5)
            except Exception as e:
                print(f"Quality analysis error: {e}")
            
            # Calculate final score from HF analysis
            hf_score = None
            if sentiment_score is not None or quality_score is not None:
                scores = []
                if sentiment_score is not None:
                    # Map sentiment to score (positive = high, negative = low)
                    if 'positive' in str(sentiment_label).lower():
                        scores.append(8.0 * sentiment_score)
                    elif 'negative' in str(sentiment_label).lower():
                        scores.append(3.0 * sentiment_score)
                    else:
                        scores.append(5.0 * sentiment_score)
                
                if quality_score is not None:
                    scores.append(quality_score)
                
                if scores:
                    hf_score = min(10.0, max(0.0, sum(scores) / len(scores)))
            
            # Generate feedback based on HF analysis
            feedback = None
            if hf_score is not None:
                if hf_score >= 8.0:
                    feedback = "Excellent answer! Your response demonstrates strong understanding and clarity. "
                elif hf_score >= 6.0:
                    feedback = "Good answer. You've covered the main points well. "
                elif hf_score >= 4.0:
                    feedback = "Average answer. Consider providing more specific details and examples. "
                else:
                    feedback = "Your answer could be improved. Try to be more specific and structured. "
                
                if expected_keywords:
                    missing_keywords = [kw for kw in expected_keywords if kw.lower() not in answer.lower()]
                    if missing_keywords and hf_score < 7.0:
                        feedback += f"Consider mentioning: {', '.join(missing_keywords[:3])}."
            
            # Prepare analysis dict
            analysis = {
                'sentiment': {
                    'label': sentiment_label,
                    'score': sentiment_score
                } if sentiment_label else None,
                'quality_score': quality_score,
                'hf_score': hf_score
            }
            
            return hf_score, feedback, analysis
            
        except Exception as e:
            print(f"Error in HF API analysis: {e}")
            return None, None, None
    
    def _analyze_with_router_api(self, question, answer, expected_keywords):
        """Analyze answer using Router API"""
        try:
            print("🔄 Calling Router API for answer analysis...")
            
            prompt = f"""Analyze this interview answer and provide a score from 0-10, feedback, and analysis.

Question: {question}
Answer: {answer}
Expected keywords/topics: {', '.join(expected_keywords) if expected_keywords else 'general response'}

Provide analysis in JSON format:
{{
  "score": 7.5,
  "feedback": "Brief feedback on the answer",
  "analysis": {{
    "strengths": ["list of strengths"],
    "weaknesses": ["list of weaknesses"],
    "keyword_coverage": 0.8
  }}
}}

Score the answer based on:
- Relevance to the question
- Use of expected keywords
- Clarity and structure
- Depth of knowledge
- Communication skills"""

            headers = {
                "Authorization": f"Bearer {self.router_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost:5000",
                "X-Title": "AI Hiring Interview Platform"
            }
            
            payload = {
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are an expert interviewer. Analyze interview answers and provide scores and feedback in valid JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(
                self.router_api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Extract JSON
                try:
                    # Find JSON in content
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    if start != -1 and end > start:
                        json_str = content[start:end]
                        analysis_data = json.loads(json_str)
                        
                        score = analysis_data.get('score')
                        feedback = analysis_data.get('feedback')
                        analysis = analysis_data.get('analysis', {})
                        
                        return score, feedback, analysis
                except json.JSONDecodeError:
                    print(f"Failed to parse Router API response as JSON: {content}")
            
            return None, None, None
            
        except Exception as e:
            print(f"Error in Router API analysis: {e}")
            return None, None, None
    
    def _analyze_with_deepseek_api(self, question, answer, expected_keywords):
        """Analyze answer using DeepSeek API"""
        try:
            print("🔄 Calling DeepSeek API for answer analysis...")
            
            prompt = f"""Analyze this interview answer and provide a score from 0-10, feedback, and analysis.

Question: {question}
Answer: {answer}
Expected keywords/topics: {', '.join(expected_keywords) if expected_keywords else 'general response'}

Provide analysis in JSON format:
{{
  "score": 7.5,
  "feedback": "Brief feedback on the answer",
  "analysis": {{
    "strengths": ["list of strengths"],
    "weaknesses": ["list of weaknesses"],
    "keyword_coverage": 0.8
  }}
}}

Score the answer based on:
- Relevance to the question
- Use of expected keywords
- Clarity and structure
- Depth of knowledge
- Communication skills"""

            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are an expert interviewer. Analyze interview answers and provide scores and feedback in valid JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(
                self.deepseek_api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Extract JSON
                try:
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    if start != -1 and end > start:
                        json_str = content[start:end]
                        analysis_data = json.loads(json_str)
                        
                        score = analysis_data.get('score')
                        feedback = analysis_data.get('feedback')
                        analysis = analysis_data.get('analysis', {})
                        
                        return score, feedback, analysis
                except json.JSONDecodeError:
                    print(f"Failed to parse DeepSeek API response as JSON: {content}")
            
            return None, None, None
            
        except Exception as e:
            print(f"Error in DeepSeek API analysis: {e}")
            return None, None, None
    
    def generate_overall_feedback(self, responses, resume_analysis):
        if not responses:
            return "No responses to evaluate."
        
        total_score = sum(response['score'] for response in responses)
        average_score = total_score / len(responses)
        
        # Try to generate feedback using Hugging Face API
        try:
            all_answers = " ".join([r.get('answer', '') for r in responses[:5]])
            
            headers = {
                "Authorization": f"Bearer {self.hf_api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""Based on these interview responses with an average score of {average_score:.1f}/10, provide overall feedback:
{all_answers[:500]}

Provide brief, constructive feedback:"""
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.7
                }
            }
            
            # Use correct Hugging Face Inference API endpoint
            model_name = Config.QUESTION_GENERATION_MODEL
            api_endpoint = f"https://api-inference.huggingface.co/models/{model_name}"
            
            response = requests.post(
                api_endpoint,
                headers=headers,
                json=payload,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list):
                    hf_feedback = result[0].get('generated_text', '')
                    if hf_feedback and len(hf_feedback) > 20:
                        return hf_feedback
        except Exception as e:
            print(f"Error generating HF feedback: {e}")
        
        # Fallback to basic feedback
        if average_score >= 8:
            strength = "strong"
        elif average_score >= 6:
            strength = "good"
        elif average_score >= 4:
            strength = "average"
        else:
            strength = "needs improvement"
        
        return f"Overall, you demonstrated {strength} performance in this interview with an average score of {average_score:.1f}/10."
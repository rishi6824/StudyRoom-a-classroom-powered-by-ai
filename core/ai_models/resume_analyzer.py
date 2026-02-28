try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
from docx import Document
import re
import os
import requests
import json
import hashlib
from difflib import SequenceMatcher
from .config import Config

class ResumeAnalyzer:
    def __init__(self):
        self.api_key = Config.HUGGINGFACE_API_KEY
        self.api_url = Config.HUGGINGFACE_API_URL
        self.sentiment_model = Config.SENTIMENT_MODEL
        self.analysis_model = Config.ANSWER_ANALYSIS_MODEL
        
        # Initialize resume database for uniqueness checking
        self.resume_db_path = os.path.join(os.path.dirname(__file__), '../data/resumes')
        os.makedirs(self.resume_db_path, exist_ok=True)
        self.resume_fingerprints_file = os.path.join(self.resume_db_path, 'resume_fingerprints.json')
        self._ensure_fingerprints_db()
        
        self.skill_categories = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin'],
            'web_tech': ['html', 'css', 'react', 'angular', 'vue', 'django', 'flask', 'node.js', 'express'],
            'databases': ['mysql', 'postgresql', 'mongodb', 'redis', 'sqlite', 'oracle'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins'],
            'data_science': ['pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn', 'r', 'matplotlib'],
            'soft_skills': ['communication', 'leadership', 'teamwork', 'problem-solving', 'creativity', 'adaptability']
        }
    
    def parse_resume(self, file_path):
        filename = file_path.lower()
        
        if filename.endswith('.pdf'):
            return self._parse_pdf(file_path)
        elif filename.endswith('.docx'):
            return self._parse_docx(file_path)
        elif filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError("Unsupported file format")
    
    def _parse_pdf(self, file_path):
        if not PDF_SUPPORT:
            return "PDF parsing not available - PyPDF2 not installed"

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    def _parse_docx(self, file_path):
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            return f"Error reading DOCX: {str(e)}"
    
    def analyze_resume_file(self, file_path):
        text = self.parse_resume(file_path)
        return self.analyze_resume_text(text)
    
    def analyze_resume_text(self, text):
        analysis = {}
        
        # Basic text analysis
        words = text.split()
        analysis['word_count'] = len(words)
        analysis['char_count'] = len(text)
        
        # Extract skills
        analysis['skills'] = self._extract_skills(text)
        
        # Extract experience
        analysis['experience'] = self._extract_experience(text)
        
        # Extract education
        analysis['education'] = self._extract_education(text)
        
        # Calculate scores
        analysis['scores'] = self._calculate_scores(text, analysis['skills'])
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        # Check for plagiarism/copying
        plagiarism_result = self._get_plagiarism_percentage(text)
        analysis['plagiarism'] = plagiarism_result
        
        return analysis
    
    def _extract_skills(self, text):
        text_lower = text.lower()
        found_skills = {}
        
        for category, skills in self.skill_categories.items():
            category_skills = []
            for skill in skills:
                if skill in text_lower:
                    category_skills.append(skill.title())
            
            if category_skills:
                found_skills[category] = category_skills
        
        return found_skills
    
    def _extract_experience(self, text):
        experience = {}
        
        # Extract years of experience
        years_pattern = r'(\d+)\s*(?:\+)?\s*years?(?:\s+of)?\s*experience'
        match = re.search(years_pattern, text, re.IGNORECASE)
        experience['years'] = match.group(1) if match else "Not specified"
        
        return experience
    
    def _extract_education(self, text):
        education = {}
        
        # Extract degrees
        degrees = ['bachelor', 'master', 'phd', 'mba', 'b\.?tech', 'm\.?tech', 'b\.?e', 'm\.?e']
        degree_pattern = r'\b(' + '|'.join(degrees) + r')\b'
        matches = re.findall(degree_pattern, text, re.IGNORECASE)
        education['degrees'] = list(set(matches))
        
        return education
    
    def _calculate_scores(self, text, skills):
        """Calculate scores using Hugging Face API for all predictions"""
        scores = {}
        
        # Try to use Hugging Face API for predictions
        hf_scores = self._predict_scores_with_hf(text, skills)
        
        if hf_scores:
            # Use Hugging Face predictions
            scores = hf_scores
        else:
            # Fallback to basic calculations if API fails
            total_skills = sum(len(skills_list) for skills_list in skills.values())
            scores['skills_score'] = min(10, total_skills / 2)
            
            exp_score = 0
            if any(str(i) in text for i in range(1, 6)):
                exp_score = min(10, 5)
            scores['experience_score'] = exp_score
            
            edu_score = min(10, len(self._extract_education(text)['degrees']) * 3)
            scores['education_score'] = edu_score
            
            scores['overall_score'] = (scores['skills_score'] + scores['experience_score'] + scores['education_score']) / 3
        
        return scores
    
    def _predict_scores_with_hf(self, text, skills):
        """Use Hugging Face API to predict resume scores"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Prepare resume summary for analysis
            total_skills = sum(len(skills_list) for skills_list in skills.values())
            skills_summary = ", ".join([skill for skill_list in skills.values() for skill in skill_list[:5]])
            education = self._extract_education(text)
            experience = self._extract_experience(text)
            
            # Create prompt for resume evaluation
            resume_summary = f"""Resume Analysis:
Skills found: {skills_summary} (Total: {total_skills} skills)
Education: {', '.join(education.get('degrees', [])) if education.get('degrees') else 'Not specified'}
Experience: {experience.get('years', 'Not specified')} years
Resume length: {len(text)} characters

Evaluate this resume on a scale of 0-10 for:
1. Skills Score (based on technical skills found)
2. Experience Score (based on years of experience and achievements)
3. Education Score (based on degrees and qualifications)
4. Overall Score (composite of all factors)

Return scores as JSON: {{"skills_score": X, "experience_score": Y, "education_score": Z, "overall_score": W}}
Scores should be between 0.0 and 10.0."""
            
            # Use text generation model for evaluation
            payload = {
                "inputs": resume_summary,
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.3,
                    "return_full_text": False
                }
            }
            
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
                generated_text = result[0].get('generated_text', '') if isinstance(result, list) else result.get('generated_text', '')
                
                # Try to extract JSON from response
                try:
                    json_start = generated_text.find('{')
                    json_end = generated_text.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_text = generated_text[json_start:json_end]
                        hf_scores = json.loads(json_text)
                        
                        # Validate and normalize scores
                        validated_scores = {}
                        for key in ['skills_score', 'experience_score', 'education_score', 'overall_score']:
                            score = hf_scores.get(key, 0)
                            # Ensure score is between 0-10
                            validated_scores[key] = max(0.0, min(10.0, float(score)))
                        
                        # Recalculate overall if not provided or recalculate average
                        if 'overall_score' not in validated_scores or not validated_scores['overall_score']:
                            validated_scores['overall_score'] = sum([
                                validated_scores.get('skills_score', 0),
                                validated_scores.get('experience_score', 0),
                                validated_scores.get('education_score', 0)
                            ]) / 3
                        
                        return validated_scores
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    print(f"Error parsing HF response: {e}")
            
            # Alternative: Use zero-shot classification for each aspect
            return self._predict_scores_with_classification(text, skills, headers)
            
        except Exception as e:
            print(f"Error in HF resume scoring: {e}")
            return None
    
    def _predict_scores_with_classification(self, text, skills, headers):
        """Use Hugging Face classification models to predict scores"""
        try:
            scores = {}
            
            # Prepare text segments for evaluation
            total_skills = sum(len(skills_list) for skills_list in skills.values())
            skills_text = f"Resume has {total_skills} technical skills: {', '.join([skill for skill_list in skills.values() for skill in skill_list[:3]])}"
            
            # Use classification model to evaluate each aspect
            # For skills score
            try:
                skills_payload = {
                    "inputs": skills_text,
                    "parameters": {
                        "candidate_labels": ["excellent (8-10)", "good (6-7)", "average (4-5)", "poor (0-3)"],
                        "multi_label": False
                    }
                }
                
                if '/mnli' in self.analysis_model or '/bart' in self.analysis_model:
                    api_endpoint = f"https://api-inference.huggingface.co/models/{self.analysis_model}"
                    response = requests.post(api_endpoint, headers=headers, json=skills_payload, timeout=15)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, list):
                            result = result[0]
                        if isinstance(result, list):
                            result = result[0]
                        
                        label = result.get('label', '').lower()
                        score_value = result.get('score', 0.5)
                        
                        # Map labels to scores
                        if 'excellent' in label:
                            scores['skills_score'] = 8.0 + (score_value * 2.0)
                        elif 'good' in label:
                            scores['skills_score'] = 6.0 + (score_value * 1.0)
                        elif 'average' in label:
                            scores['skills_score'] = 4.0 + (score_value * 1.0)
                        else:
                            scores['skills_score'] = score_value * 3.0
                        
                        scores['skills_score'] = max(0.0, min(10.0, scores['skills_score']))
            except Exception as e:
                print(f"Error in skills classification: {e}")
            
            # For experience and education, use similar approach
            # Experience evaluation
            experience = self._extract_experience(text)
            exp_text = f"Resume shows {experience.get('years', 'unspecified')} years of experience"
            
            try:
                exp_payload = {
                    "inputs": exp_text,
                    "parameters": {
                        "candidate_labels": ["strong experience (8-10)", "moderate experience (5-7)", "limited experience (2-4)", "minimal experience (0-2)"],
                        "multi_label": False
                    }
                }
                
                if '/mnli' in self.analysis_model:
                    api_endpoint = f"https://api-inference.huggingface.co/models/{self.analysis_model}"
                    response = requests.post(api_endpoint, headers=headers, json=exp_payload, timeout=15)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, list):
                            result = result[0]
                        if isinstance(result, list):
                            result = result[0]
                        
                        label = result.get('label', '').lower()
                        score_value = result.get('score', 0.5)
                        
                        if 'strong' in label:
                            scores['experience_score'] = 8.0 + (score_value * 2.0)
                        elif 'moderate' in label:
                            scores['experience_score'] = 5.0 + (score_value * 2.0)
                        elif 'limited' in label:
                            scores['experience_score'] = 2.0 + (score_value * 2.0)
                        else:
                            scores['experience_score'] = score_value * 2.0
                        
                        scores['experience_score'] = max(0.0, min(10.0, scores['experience_score']))
            except Exception as e:
                print(f"Error in experience classification: {e}")
            
            # Education evaluation
            education = self._extract_education(text)
            edu_text = f"Resume shows education: {', '.join(education.get('degrees', [])) if education.get('degrees') else 'Not specified'}"
            
            try:
                edu_payload = {
                    "inputs": edu_text,
                    "parameters": {
                        "candidate_labels": ["highly qualified (8-10)", "well qualified (6-7)", "adequately qualified (4-5)", "needs improvement (0-3)"],
                        "multi_label": False
                    }
                }
                
                if '/mnli' in self.analysis_model:
                    api_endpoint = f"https://api-inference.huggingface.co/models/{self.analysis_model}"
                    response = requests.post(api_endpoint, headers=headers, json=edu_payload, timeout=15)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, list):
                            result = result[0]
                        if isinstance(result, list):
                            result = result[0]
                        
                        label = result.get('label', '').lower()
                        score_value = result.get('score', 0.5)
                        
                        if 'highly' in label:
                            scores['education_score'] = 8.0 + (score_value * 2.0)
                        elif 'well' in label:
                            scores['education_score'] = 6.0 + (score_value * 1.0)
                        elif 'adequately' in label:
                            scores['education_score'] = 4.0 + (score_value * 1.0)
                        else:
                            scores['education_score'] = score_value * 3.0
                        
                        scores['education_score'] = max(0.0, min(10.0, scores['education_score']))
            except Exception as e:
                print(f"Error in education classification: {e}")
            
            # Calculate overall score
            if scores:
                # Fill missing scores with defaults
                if 'skills_score' not in scores:
                    total_skills = sum(len(skills_list) for skills_list in skills.values())
                    scores['skills_score'] = min(10, total_skills / 2)
                
                if 'experience_score' not in scores:
                    scores['experience_score'] = 5.0
                
                if 'education_score' not in scores:
                    edu = self._extract_education(text)
                    scores['education_score'] = min(10, len(edu.get('degrees', [])) * 3)
                
                scores['overall_score'] = (
                    scores.get('skills_score', 0) + 
                    scores.get('experience_score', 0) + 
                    scores.get('education_score', 0)
                ) / 3
                
                return scores
                
        except Exception as e:
            print(f"Error in classification-based scoring: {e}")
        
        return None
    
    def _generate_recommendations(self, analysis):
        """Generate recommendations using Hugging Face API"""
        # Try to generate with Hugging Face API
        hf_recommendations = self._generate_recommendations_with_hf(analysis)
        
        if hf_recommendations and len(hf_recommendations) > 0:
            return hf_recommendations
        
        # Fallback to basic recommendations
        recommendations = []
        scores = analysis['scores']
        
        if scores['skills_score'] < 6:
            recommendations.append("Consider adding more technical skills to your resume")
        
        if scores['experience_score'] < 5:
            recommendations.append("Highlight your work experience with specific achievements")
        
        if analysis['word_count'] < 200:
            recommendations.append("Your resume seems brief. Consider adding more details about your projects and achievements")
        
        if not recommendations:
            recommendations.append("Your resume looks strong! Focus on preparing for behavioral questions")
        
        return recommendations
    
    def _generate_recommendations_with_hf(self, analysis):
        """Use Hugging Face API to generate personalized recommendations"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            scores = analysis['scores']
            skills = analysis.get('skills', {})
            word_count = analysis.get('word_count', 0)
            
            # Create prompt for recommendations
            prompt = f"""Based on this resume analysis:
- Skills Score: {scores.get('skills_score', 0):.1f}/10
- Experience Score: {scores.get('experience_score', 0):.1f}/10
- Education Score: {scores.get('education_score', 0):.1f}/10
- Overall Score: {scores.get('overall_score', 0):.1f}/10
- Resume length: {word_count} words
- Skills found: {len([s for skill_list in skills.values() for s in skill_list])} technical skills

Provide 2-3 specific, actionable recommendations to improve this resume. 
Format as a JSON array of strings: ["recommendation1", "recommendation2", "recommendation3"]

Recommendations:"""
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 300,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }
            
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
                generated_text = result[0].get('generated_text', '') if isinstance(result, list) else result.get('generated_text', '')
                
                # Try to extract JSON array from response
                try:
                    json_start = generated_text.find('[')
                    json_end = generated_text.rfind(']') + 1
                    if json_start != -1 and json_end > json_start:
                        json_text = generated_text[json_start:json_end]
                        recommendations = json.loads(json_text)
                        
                        # Validate and clean recommendations
                        if isinstance(recommendations, list):
                            cleaned = [str(r).strip() for r in recommendations if r and len(str(r).strip()) > 10]
                            if cleaned:
                                return cleaned[:4]  # Limit to 4 recommendations
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing HF recommendations: {e}")
                    
                    # Try to extract recommendations from text
                    lines = generated_text.split('\n')
                    recommendations = []
                    for line in lines:
                        line = line.strip().lstrip('- ').lstrip('* ').strip()
                        if line and len(line) > 15 and ('recommend' in line.lower() or 'suggest' in line.lower() or 'improve' in line.lower() or 'add' in line.lower()):
                            recommendations.append(line)
                            if len(recommendations) >= 3:
                                break
                    
                    if recommendations:
                        return recommendations
                        
        except Exception as e:
            print(f"Error generating HF recommendations: {e}")
        
        return None
    
    def _ensure_fingerprints_db(self):
        """Ensure the fingerprints database file exists"""
        if not os.path.exists(self.resume_fingerprints_file):
            with open(self.resume_fingerprints_file, 'w') as f:
                json.dump({'resumes': []}, f, indent=2)
    
    def _extract_key_features(self, text):
        """
        Extract key features for uniqueness checking:
        - Skills
        - Education
        - Years of experience
        - Projects/achievements
        """
        text_lower = text.lower()
        features = {}
        
        # Extract skills
        features['skills'] = self._extract_skills(text)
        
        # Extract education
        education = self._extract_education(text)
        features['education'] = education.get('degrees', [])
        
        # Extract experience
        experience = self._extract_experience(text)
        features['experience'] = experience.get('years', 'Not specified')
        
        # Extract projects (look for common project keywords)
        project_keywords = ['project', 'developed', 'built', 'created', 'designed', 'implemented', 'led']
        projects = []
        sentences = re.split(r'[.!?]', text)
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in project_keywords):
                # Extract project name and description
                project_summary = sentence.strip()[:100]
                if project_summary and len(project_summary) > 10:
                    projects.append(project_summary.lower())
        
        features['projects'] = projects[:5]  # Limit to 5 projects
        
        # Extract career insights (titles, companies)
        title_keywords = ['developer', 'engineer', 'manager', 'analyst', 'architect', 'lead', 'senior', 'junior']
        roles = []
        for title_kw in title_keywords:
            if title_kw in text_lower:
                roles.append(title_kw)
        
        features['roles'] = list(set(roles))
        
        return features
    
    def _compute_resume_fingerprint(self, features):
        """
        Compute a fingerprint hash of the resume based on key features
        """
        # Flatten all features into a string for hashing
        fingerprint_data = {
            'skills': sorted([s for skill_list in features.get('skills', {}).values() for s in skill_list]),
            'education': sorted(features.get('education', [])),
            'experience': features.get('experience', ''),
            'projects': sorted(features.get('projects', [])),
            'roles': sorted(features.get('roles', []))
        }
        
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()
        
        return fingerprint_hash, fingerprint_data
    
    def _calculate_similarity(self, features1, features2):
        """
        Calculate similarity score between two resume feature sets.
        Returns a score between 0 and 1, where 1 is identical.
        """
        similarity_scores = []
        
        # Skills similarity
        skills1 = set(s for skill_list in features1.get('skills', {}).values() for s in skill_list)
        skills2 = set(s for skill_list in features2.get('skills', {}).values() for s in skill_list)
        if skills1 or skills2:
            skills_similarity = len(skills1 & skills2) / len(skills1 | skills2) if (skills1 | skills2) else 0
            similarity_scores.append(skills_similarity * 0.4)  # Weight skills at 40%
        
        # Education similarity
        edu1 = set(features1.get('education', []))
        edu2 = set(features2.get('education', []))
        if edu1 or edu2:
            edu_similarity = len(edu1 & edu2) / len(edu1 | edu2) if (edu1 | edu2) else 0
            similarity_scores.append(edu_similarity * 0.15)  # Weight education at 15%
        
        # Experience similarity
        exp1 = str(features1.get('experience', '')).lower()
        exp2 = str(features2.get('experience', '')).lower()
        exp_similarity = SequenceMatcher(None, exp1, exp2).ratio()
        similarity_scores.append(exp_similarity * 0.15)  # Weight experience at 15%
        
        # Projects similarity
        projects1 = features1.get('projects', [])
        projects2 = features2.get('projects', [])
        project_matches = sum(1 for p1 in projects1 for p2 in projects2 if SequenceMatcher(None, p1, p2).ratio() > 0.7)
        projects_similarity = project_matches / max(len(projects1), len(projects2), 1)
        similarity_scores.append(projects_similarity * 0.2)  # Weight projects at 20%
        
        # Roles similarity
        roles1 = set(features1.get('roles', []))
        roles2 = set(features2.get('roles', []))
        if roles1 or roles2:
            roles_similarity = len(roles1 & roles2) / len(roles1 | roles2) if (roles1 | roles2) else 0
            similarity_scores.append(roles_similarity * 0.1)  # Weight roles at 10%
        
        total_similarity = sum(similarity_scores)
        return total_similarity
    
    def _check_resume_uniqueness(self, features, similarity_threshold=0.75):
        """
        Check if the resume is unique by comparing with existing resumes.
        Returns (is_unique, most_similar_score, error_message)
        
        similarity_threshold: Resumes with similarity >= this value are considered duplicates
        """
        try:
            with open(self.resume_fingerprints_file, 'r') as f:
                data = json.load(f)
                existing_resumes = data.get('resumes', [])
            
            if not existing_resumes:
                # First resume is always unique
                return True, 0.0, None
            
            max_similarity = 0.0
            most_similar_features = None
            
            for existing_resume in existing_resumes:
                existing_features = existing_resume.get('features', {})
                similarity_score = self._calculate_similarity(features, existing_features)
                
                if similarity_score > max_similarity:
                    max_similarity = similarity_score
                    most_similar_features = existing_resume
            
            # Check if similarity exceeds threshold
            if max_similarity >= similarity_threshold:
                error_msg = (
                    f"❌ Resume Upload Failed: This resume is too similar to an existing resume. "
                    f"Similarity Score: {max_similarity:.1%}\n\n"
                    f"Your resume must be unique with distinct:\n"
                    f"✓ Career insights and professional roles\n"
                    f"✓ Technical skills and expertise areas\n"
                    f"✓ Projects and accomplishments\n\n"
                    f"Please upload a resume that represents a different professional profile."
                )
                return False, max_similarity, error_msg
            
            return True, max_similarity, None
            
        except Exception as e:
            print(f"Error checking resume uniqueness: {e}")
            # If there's an error, allow the resume (fail-open)
            return True, 0.0, None
    
    def _store_resume_fingerprint(self, fingerprint_hash, features):
        """
        Store the resume fingerprint for future uniqueness checks
        """
        try:
            with open(self.resume_fingerprints_file, 'r') as f:
                data = json.load(f)
            
            # Add new resume fingerprint
            resume_entry = {
                'hash': fingerprint_hash,
                'features': features,
                'timestamp': str(os.popen('date').read().strip())
            }
            
            data['resumes'].append(resume_entry)
            
            with open(self.resume_fingerprints_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error storing resume fingerprint: {e}")
            return False
    
    def check_and_validate_resume(self, text):
        """
        Main method to check if a resume is unique.
        Returns (is_valid, error_message)
        """
        features = self._extract_key_features(text)
        fingerprint_hash, fingerprint_data = self._compute_resume_fingerprint(features)
        
        is_unique, similarity_score, error_msg = self._check_resume_uniqueness(features, similarity_threshold=0.75)
        
        if is_unique:
            # Store this fingerprint for future comparisons
            self._store_resume_fingerprint(fingerprint_hash, fingerprint_data)
            return True, None
        else:
            return False, error_msg
    
    def _detect_plagiarism_hf(self, text):
        """
        Detect plagiarism using Hugging Face API.
        Compares resume text against common resume patterns and templates.
        Returns plagiarism percentage (0-100).
        """
        try:
            if not self.api_key:
                return None
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Create comparison prompts for plagiarism detection
            plagiarism_prompt = f"""Analyze this resume for plagiarism and template usage. 
Identify sections that appear to be copied from templates or other standard resumes.
Resume text:
{text}

Provide analysis in JSON format: {{"plagiarism_percentage": X, "detected_templates": ["template1", "template2"], "suspicious_sections": ["section1", "section2"]}}
Plagiarism percentage should be 0-100 where 100 is completely copied."""
            
            payload = {
                "inputs": plagiarism_prompt,
                "parameters": {
                    "max_new_tokens": 300,
                    "temperature": 0.3,
                    "return_full_text": False
                }
            }
            
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
                generated_text = result[0].get('generated_text', '') if isinstance(result, list) else result.get('generated_text', '')
                
                # Try to extract JSON from response
                try:
                    json_start = generated_text.find('{')
                    json_end = generated_text.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_text = generated_text[json_start:json_end]
                        plagiarism_data = json.loads(json_text)
                        
                        plagiarism_percent = plagiarism_data.get('plagiarism_percentage', 0)
                        # Ensure it's between 0-100
                        plagiarism_percent = max(0, min(100, float(plagiarism_percent)))
                        
                        return {
                            'percentage': plagiarism_percent,
                            'detected_templates': plagiarism_data.get('detected_templates', []),
                            'suspicious_sections': plagiarism_data.get('suspicious_sections', []),
                            'source': 'huggingface'
                        }
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    print(f"Error parsing HF plagiarism response: {e}")
                    return None
            
            return None
            
        except Exception as e:
            print(f"Error in HF plagiarism detection: {e}")
            return None
    
    def _detect_plagiarism_router_ai(self, text):
        """
        Detect plagiarism using Router AI (OpenRouter) API.
        Uses advanced AI models to identify copied content and lack of authenticity.
        Returns plagiarism percentage (0-100).
        """
        try:
            if not Config.ROUTER_API_KEY:
                return None
            
            headers = {
                "Authorization": f"Bearer {Config.ROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Create plagiarism detection prompt
            plagiarism_prompt = f"""You are an expert resume plagiarism detector. Analyze this resume for:
1. Copied content from job descriptions or templates
2. Generic/templated language vs personal authentic writing
3. Inconsistencies that suggest copying
4. Overuse of buzzwords without context

Resume:
{text}

Respond ONLY with JSON (no markdown, no code blocks):
{{"plagiarism_percentage": integer 0-100, "authenticity_score": integer 0-100, "observations": ["observation1", "observation2"], "risk_level": "low/medium/high"}}

Plagiarism % = how much appears copied (100 = fully plagiarized)
Authenticity = how genuine/personal it sounds (100 = completely authentic)
Risk level = hiring risk due to plagiarism"""
            
            payload = {
                "model": "gpt-3.5-turbo",  # Using a capable model via OpenRouter
                "messages": [
                    {
                        "role": "user",
                        "content": plagiarism_prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 300
            }
            
            response = requests.post(
                Config.ROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                message_content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Try to extract JSON from response
                try:
                    json_start = message_content.find('{')
                    json_end = message_content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_text = message_content[json_start:json_end]
                        plagiarism_data = json.loads(json_text)
                        
                        plagiarism_percent = plagiarism_data.get('plagiarism_percentage', 0)
                        authenticity_score = plagiarism_data.get('authenticity_score', 50)
                        
                        # Ensure values are in valid ranges
                        plagiarism_percent = max(0, min(100, float(plagiarism_percent)))
                        authenticity_score = max(0, min(100, float(authenticity_score)))
                        
                        return {
                            'percentage': plagiarism_percent,
                            'authenticity_score': authenticity_score,
                            'observations': plagiarism_data.get('observations', []),
                            'risk_level': plagiarism_data.get('risk_level', 'unknown'),
                            'source': 'router_ai'
                        }
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    print(f"Error parsing Router AI response: {e}")
                    return None
            else:
                print(f"Router AI API error: {response.status_code}")
                return None
            
            return None
            
        except Exception as e:
            print(f"Error in Router AI plagiarism detection: {e}")
            return None
    
    def _get_plagiarism_percentage(self, text):
        """
        Get overall plagiarism detection score using multiple sources.
        Combines Hugging Face and Router AI results.
        Returns comprehensive plagiarism analysis.
        """
        try:
            # Get plagiarism scores from both sources
            hf_result = self._detect_plagiarism_hf(text)
            router_result = self._detect_plagiarism_router_ai(text)
            
            overall_result = {
                'percentage': 0.0,
                'authenticity_score': 50.0,
                'risk_level': 'low',
                'sources_checked': [],
                'details': {}
            }
            
            plagiarism_scores = []
            
            # Process Hugging Face result
            if hf_result:
                overall_result['sources_checked'].append('huggingface')
                overall_result['details']['huggingface'] = {
                    'percentage': hf_result.get('percentage', 0),
                    'detected_templates': hf_result.get('detected_templates', []),
                    'suspicious_sections': hf_result.get('suspicious_sections', [])
                }
                plagiarism_scores.append(hf_result.get('percentage', 0))
            
            # Process Router AI result
            if router_result:
                overall_result['sources_checked'].append('router_ai')
                overall_result['details']['router_ai'] = {
                    'percentage': router_result.get('percentage', 0),
                    'authenticity_score': router_result.get('authenticity_score', 50),
                    'observations': router_result.get('observations', []),
                    'risk_level': router_result.get('risk_level', 'unknown')
                }
                plagiarism_scores.append(router_result.get('percentage', 0))
                overall_result['authenticity_score'] = router_result.get('authenticity_score', 50)
                overall_result['risk_level'] = router_result.get('risk_level', 'low')
            
            # Calculate overall plagiarism percentage (average of all sources)
            if plagiarism_scores:
                overall_result['percentage'] = sum(plagiarism_scores) / len(plagiarism_scores)
            
            # If no sources available, return default
            if not overall_result['sources_checked']:
                return {
                    'percentage': 0.0,
                    'authenticity_score': 50.0,
                    'risk_level': 'unknown',
                    'sources_checked': [],
                    'details': {},
                    'message': 'Plagiarism detection unavailable - API keys not configured'
                }
            
            # Determine final risk level based on plagiarism percentage
            if overall_result['percentage'] >= 70:
                overall_result['risk_level'] = 'high'
            elif overall_result['percentage'] >= 40:
                overall_result['risk_level'] = 'medium'
            else:
                overall_result['risk_level'] = 'low'
            
            return overall_result
            
        except Exception as e:
            print(f"Error in plagiarism detection: {e}")
            return {
                'percentage': 0.0,
                'authenticity_score': 50.0,
                'risk_level': 'unknown',
                'sources_checked': [],
                'details': {},
                'error': str(e)
            }
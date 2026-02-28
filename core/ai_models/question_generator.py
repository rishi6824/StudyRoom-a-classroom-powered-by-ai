import random
import requests
import json
from .config import Config

class QuestionGenerator:
    def __init__(self):
        # API Keys from Config
        self.router_api_key = Config.ROUTER_API_KEY
        self.deepseek_api_key = Config.DEEPSEEK_API_KEY
        self.hf_api_key = Config.HUGGINGFACE_API_KEY
        self.hf_api_url = Config.HUGGINGFACE_API_URL
        self.hf_model = Config.QUESTION_GENERATION_MODEL
        
        # API Endpoints
        self.router_api_url = Config.ROUTER_API_URL
        self.deepseek_api_url = Config.DEEPSEEK_API_URL

        # Load base questions from JSON (fallback when APIs or keys are unavailable)
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_questions_file = os.path.join(base_dir, 'data', 'questions', 'interview_questions.json')
        try:
            with open(self.base_questions_file, 'r') as f:
                self.base_questions = json.load(f)
                print(f"✅ Loaded base questions from {self.base_questions_file}")
        except Exception as e:
            print(f"⚠️ Could not load base questions file {self.base_questions_file}: {e}\nUsing minimal embedded defaults")
            # Minimal embedded defaults if JSON not present
            self.base_questions = {
                "software_engineer": [
                    {"question": "Explain object-oriented programming and its main principles.", "type": "technical", "difficulty": "medium"},
                    {"question": "Describe a challenging technical problem you solved and how you approached it.", "type": "behavioral", "difficulty": "medium"},
                    {"question": "How do you ensure code quality and what testing methodologies do you use?", "type": "technical", "difficulty": "medium"}
                ]
            }
        # Last generation source ('router','deepseek','hf','local','mixed','generic')
        self.last_generation_source = None
    
    def generate_questions_raw(self, job_role, resume_analysis, num_questions=3):
        """
        Generate exactly num_questions questions using multiple APIs in sequence:
        1. Router API (primary)
        2. DeepSeek API (secondary)
        3. Hugging Face API (tertiary)
        """
        num_questions = max(1, int(num_questions))

        # Try Router API first
        if self.router_api_key:
            router_questions = self._generate_with_router_api(job_role, resume_analysis, num_questions)
            if router_questions and len(router_questions) >= num_questions:
                print(f"✅ Generated {len(router_questions)} questions using Router API")
                self.last_generation_source = 'router'
                return router_questions[:num_questions]
        else:
            print("ℹ️ Skipping Router API: No API key provided")
            
        # Try DeepSeek API second
        if self.deepseek_api_key:
            deepseek_questions = self._generate_with_deepseek_api(job_role, resume_analysis, num_questions)
            if deepseek_questions and len(deepseek_questions) >= num_questions:
                print(f"✅ Generated {len(deepseek_questions)} questions using DeepSeek API")
                self.last_generation_source = 'deepseek'
                return deepseek_questions[:num_questions]
        else:
            print("ℹ️ Skipping DeepSeek API: No API key provided")
            
        # Try Hugging Face API third
        if self.hf_api_key:
            hf_questions = self._generate_with_hf_api(job_role, resume_analysis, num_questions)
            if hf_questions and len(hf_questions) >= num_questions:
                print(f"✅ Generated {len(hf_questions)} questions using Hugging Face API")
                self.last_generation_source = 'hf'
                return hf_questions[:num_questions]
        else:
            print("ℹ️ Skipping Hugging Face API: No API key provided")

        # If all APIs fail, use base question bank for this role
        print("⚠️ All APIs failed, using base question bank as fallback")
        role_questions = self.base_questions.get(job_role, self.base_questions.get("software_engineer", []))
        if role_questions:
            fallback = []
            i = 0
            while len(fallback) < num_questions:
                q = role_questions[i % len(role_questions)]
                if q.get('question') not in [f.get('question') for f in fallback]:
                    fallback.append(q)
                i += 1
            self.last_generation_source = 'local'
            return fallback[:num_questions]

    def base_questions_fallback(self, job_role, num_questions):
        """Return a list of fallback questions from the local base bank."""
        role_questions = self.base_questions.get(job_role, self.base_questions.get("software_engineer", []))
        if not role_questions:
            return [{
                "question": f"Tell me about yourself and your most relevant experience for this {job_role} role.",
                "type": "behavioral",
                "difficulty": "easy"
            }]

        fallback = []
        i = 0
        while len(fallback) < num_questions:
            q = role_questions[i % len(role_questions)]
            if q.get('question') not in [f.get('question') for f in fallback]:
                fallback.append(q)
            i += 1
        self.last_generation_source = 'local'
        return fallback[:num_questions]

    def generate_next_question(self, job_role, resume_analysis, asked_questions, last_answer=None):
        """
        Generate a single next question in an 'interviewer' style, considering:
        - questions already asked (avoid duplicates)
        - last answer (to create a natural follow-up)
        Returns a dict: {question, type, difficulty}
        """
        asked_questions = asked_questions or []
        asked_texts = [q.get("question", "") for q in asked_questions if isinstance(q, dict)]
        asked_texts = [t for t in asked_texts if t]

        # Extract top skills for context
        skills_text = ""
        if resume_analysis:
            skills = resume_analysis.get('skills', {})
            skills_list = []
            for category, skill_list in skills.items():
                skills_list.extend(skill_list)
            skills_text = ", ".join(skills_list[:10])

        # Build a prompt for ONE next question
        last_answer_text = (last_answer or "").strip()
        last_answer_text = last_answer_text[:600]  # keep prompt small-ish
        recent_questions = "\n".join([f"- {t}" for t in asked_texts[-8:]]) if asked_texts else "- (none yet)"

        prompt = f"""You are an experienced human interviewer having a natural conversation with a {job_role} candidate.
{f"Candidate skills: {skills_text}" if skills_text else ""}

Previously asked questions (do NOT repeat):
{recent_questions}

{f"Candidate's last answer (for follow-up context): {last_answer_text}" if last_answer_text else ""}

Generate exactly 1 next question that feels like a natural follow-up in a real conversation. Make it sound like you're genuinely interested and building rapport, not just checking boxes.

Examples of conversational questions:
- "That sounds fascinating. What was the most challenging part of that experience for you?"
- "I'm curious - how did you decide to approach that problem?"
- "Based on what you've shared, I'd love to hear more about your experience with..."
- "That's really interesting. Can you tell me about a time when..."

Return ONLY valid JSON (no markdown) in this exact format:
{{"question":"...","type":"technical|behavioral","difficulty":"easy|medium|hard"}}"""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            api_endpoint = f"https://api-inference.huggingface.co/models/{self.model}"
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 250,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }

            response = requests.post(
                api_endpoint,
                headers=headers,
                json=payload,
                timeout=45
            )

            if response.status_code == 200:
                result = response.json()
                generated_text = result[0].get('generated_text', '') if isinstance(result, list) else result.get('generated_text', '')

                # Attempt to parse a JSON object from the response
                # Clean up potential markdown formatting
                clean_text = generated_text.replace('```json', '').replace('```', '').strip()
                
                json_start = clean_text.find('{')
                json_end = clean_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    obj_text = clean_text[json_start:json_end]
                    try:
                        q = json.loads(obj_text)
                    except json.JSONDecodeError:
                        # Try to fix common JSON errors (e.g. trailing commas)
                        try:
                            import ast
                            q = ast.literal_eval(obj_text)
                        except:
                            q = {} # Failed to parse
                    if isinstance(q, dict) and q.get("question"):
                        candidate = {
                            "question": str(q.get("question", "")).strip(),
                            "type": str(q.get("type", "technical")).strip() or "technical",
                            "difficulty": str(q.get("difficulty", "medium")).strip() or "medium"
                        }

                        # Basic duplicate protection
                        if candidate["question"] and candidate["question"] not in asked_texts:
                            return candidate

            elif response.status_code == 503:
                # Model loading; fall through to fallback
                pass
            else:
                # Fall through to fallback
                pass
        except Exception:
            # Fall through to fallback
            pass

        # Try Router API first
        router_q = self._generate_single_with_router_api(job_role, resume_analysis, asked_texts, last_answer_text)
        if router_q:
            return router_q

        # Try DeepSeek API second
        deepseek_q = self._generate_single_with_deepseek_api(job_role, resume_analysis, asked_texts, last_answer_text)
        if deepseek_q:
            return deepseek_q

        # Try Hugging Face API third
        hf_q = self._generate_single_with_hf_api(job_role, resume_analysis, asked_texts, last_answer_text)
        if hf_q:
            return hf_q

        # Minimal fallback if all APIs fail - pick from base question bank (avoid duplicates)
        role_questions = self.base_questions.get(job_role, self.base_questions.get("software_engineer", []))
        for q in role_questions:
            if q.get('question') not in asked_texts:
                return q

        # As a final fallback, return a generic question
        return {
            "question": f"Tell me about yourself and your most relevant experience for this {job_role} role.",
            "type": "behavioral",
            "difficulty": "easy"
        }

    def _generate_with_router_api(self, job_role, resume_analysis, num_questions=3):
        """Generate questions using Router API"""
        try:
            print(f"🔄 Calling Router API to generate {num_questions} questions for {job_role}...")
            
            # Extract skills from resume
            skills_text = ""
            if resume_analysis:
                skills = resume_analysis.get('skills', {})
                skills_list = []
                for category, skill_list in skills.items():
                    skills_list.extend(skill_list)
                skills_text = ", ".join(skills_list[:10])
            
            # Build the prompt using string formatting to avoid f-string backslash issues
            skills_section = f'Based on the candidate\'s background: {skills_text}' if skills_text else ''
            
            prompt = f"""You are an experienced human interviewer conducting a {job_role} interview. Generate exactly {num_questions} questions that feel natural and conversational, like a real interview.

{skills_section}

Create questions that:
- Flow naturally in a conversation
- Build on each other thematically
- Mix personal experience with technical knowledge
- Feel like they're coming from a curious, engaged interviewer
- Vary in depth from introductory to challenging
- Avoid sounding robotic or overly structured

Return questions in JSON format as a list, each with 'question', 'type' (technical/behavioral), and 'difficulty' (easy/medium/hard).

Example of natural questions:
- "I'd love to hear about your journey into {job_role} work. What drew you to this field initially?"
- "That's interesting. Can you walk me through a project where you really had to dig deep into the technical details?"
- "How do you typically approach solving problems when you're not sure where to start?"

Generate exactly {num_questions} conversational questions:"""

            headers = {
                "Authorization": f"Bearer {self.router_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost:5000",
                "X-Title": "AI Hiring Interview Platform"
            }
            
            payload = {
                "model": "openai/gpt-4o-mini",  # OpenRouter model format
                "messages": [
                    {"role": "system", "content": "You are an expert interviewer. Generate interview questions in valid JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 2000
            }
            
            response = requests.post(
                self.router_api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Extract JSON from response
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                if json_start != -1 and json_end > json_start:
                    json_text = content[json_start:json_end]
                    questions = json.loads(json_text)
                    
                    formatted_questions = []
                    for q in questions[:num_questions]:
                        if isinstance(q, dict) and 'question' in q:
                            formatted_questions.append({
                                "question": q.get('question', ''),
                                "type": q.get('type', 'technical'),
                                "difficulty": q.get('difficulty', 'medium')
                            })
                    
                    if formatted_questions:
                        print(f"✅ Successfully parsed {len(formatted_questions)} questions from Router API")
                        return formatted_questions
        except Exception as e:
            print(f"❌ Router API error: {e}")
        
        return None

    def _generate_with_deepseek_api(self, job_role, resume_analysis, num_questions=3):
        """Generate questions using DeepSeek API"""
        try:
            print(f"🔄 Calling DeepSeek API to generate {num_questions} questions for {job_role}...")
            
            # Extract skills from resume
            skills_text = ""
            if resume_analysis:
                skills = resume_analysis.get('skills', {})
                skills_list = []
                for category, skill_list in skills.items():
                    skills_list.extend(skill_list)
                skills_text = ", ".join(skills_list[:10])
            
            # Build the prompt using string formatting to avoid f-string backslash issues
            skills_section = f'Based on the candidate\'s background: {skills_text}' if skills_text else ''
            
            prompt = f"""You are an experienced human interviewer conducting a {job_role} interview. Generate exactly {num_questions} questions that feel natural and conversational, like a real interview.

{skills_section}

Create questions that:
- Flow naturally in a conversation
- Build on each other thematically
- Mix personal experience with technical knowledge
- Feel like they're coming from a curious, engaged interviewer
- Vary in depth from introductory to challenging
- Avoid sounding robotic or overly structured

Return questions in JSON format as a list, each with 'question', 'type' (technical/behavioral), and 'difficulty' (easy/medium/hard).

Example of natural questions:
- "I'd love to hear about your journey into {job_role} work. What drew you to this field initially?"
- "That's interesting. Can you walk me through a project where you really had to dig deep into the technical details?"
- "How do you typically approach solving problems when you're not sure where to start?"

Generate exactly {num_questions} conversational questions:"""

            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are an expert interviewer. Generate interview questions in valid JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 2000
            }
            
            response = requests.post(
                self.deepseek_api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Extract JSON from response
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                if json_start != -1 and json_end > json_start:
                    json_text = content[json_start:json_end]
                    questions = json.loads(json_text)
                    
                    formatted_questions = []
                    for q in questions[:num_questions]:
                        if isinstance(q, dict) and 'question' in q:
                            formatted_questions.append({
                                "question": q.get('question', ''),
                                "type": q.get('type', 'technical'),
                                "difficulty": q.get('difficulty', 'medium')
                            })
                    
                    if formatted_questions:
                        print(f"✅ Successfully parsed {len(formatted_questions)} questions from DeepSeek API")
                        return formatted_questions
        except Exception as e:
            print(f"❌ DeepSeek API error: {e}")
        
        return None

    def _generate_single_with_router_api(self, job_role, resume_analysis, asked_texts, last_answer):
        """Generate single question using Router API"""
        try:
            skills_text = ""
            if resume_analysis:
                skills = resume_analysis.get('skills', {})
                skills_list = []
                for category, skill_list in skills.items():
                    skills_list.extend(skill_list)
                skills_text = ", ".join(skills_list[:10])
            
            recent_questions = "\n".join([f"- {t}" for t in asked_texts[-8:]]) if asked_texts else "- (none yet)"
            
            prompt = f"""You are an experienced human interviewer having a natural conversation with a {job_role} candidate.
{f"Candidate skills: {skills_text}" if skills_text else ""}

Previously asked questions (do NOT repeat):
{recent_questions}

{f"Candidate's last answer (for follow-up context): {last_answer[:600]}" if last_answer else ""}

Generate exactly 1 next question that feels like a natural follow-up in a real conversation. Make it sound like you're genuinely interested and building rapport, not just checking boxes.

Examples of conversational questions:
- "That sounds fascinating. What was the most challenging part of that experience for you?"
- "I'm curious - how did you decide to approach that problem?"
- "Based on what you've shared, I'd love to hear more about your experience with..."
- "That's really interesting. Can you tell me about a time when..."

Return ONLY valid JSON (no markdown) in this exact format:
{{"question":"...","type":"technical|behavioral","difficulty":"easy|medium|hard"}}"""

            headers = {
                "Authorization": f"Bearer {self.router_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost:5000",  # OpenRouter requires this
                "X-Title": "AI Hiring Interview Platform"  # Optional but recommended
            }
            
            payload = {
                "model": "openai/gpt-4o-mini",  # OpenRouter model format
                "messages": [
                    {"role": "system", "content": "You are an expert interviewer. Return only valid JSON, no markdown."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
            
            response = requests.post(self.router_api_url, headers=headers, json=payload, timeout=45)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    q = json.loads(content[json_start:json_end])
                    if isinstance(q, dict) and q.get("question") and q.get("question") not in asked_texts:
                        return {
                            "question": str(q.get("question", "")).strip(),
                            "type": str(q.get("type", "technical")).strip() or "technical",
                            "difficulty": str(q.get("difficulty", "medium")).strip() or "medium"
                        }
        except Exception as e:
            print(f"❌ Router API single question error: {e}")
        
        return None

    def _generate_single_with_deepseek_api(self, job_role, resume_analysis, asked_texts, last_answer):
        """Generate single question using DeepSeek API"""
        try:
            skills_text = ""
            if resume_analysis:
                skills = resume_analysis.get('skills', {})
                skills_list = []
                for category, skill_list in skills.items():
                    skills_list.extend(skill_list)
                skills_text = ", ".join(skills_list[:10])
            
            recent_questions = "\n".join([f"- {t}" for t in asked_texts[-8:]]) if asked_texts else "- (none yet)"
            
            prompt = f"""You are an experienced human interviewer having a natural conversation with a {job_role} candidate.
{f"Candidate skills: {skills_text}" if skills_text else ""}

Previously asked questions (do NOT repeat):
{recent_questions}

{f"Candidate's last answer (for follow-up context): {last_answer[:600]}" if last_answer else ""}

Generate exactly 1 next question that feels like a natural follow-up in a real conversation. Make it sound like you're genuinely interested and building rapport, not just checking boxes.

Examples of conversational questions:
- "That sounds fascinating. What was the most challenging part of that experience for you?"
- "I'm curious - how did you decide to approach that problem?"
- "Based on what you've shared, I'd love to hear more about your experience with..."
- "That's really interesting. Can you tell me about a time when..."

Return ONLY valid JSON (no markdown) in this exact format:
{{"question":"...","type":"technical|behavioral","difficulty":"easy|medium|hard"}}"""

            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are an expert interviewer. Return only valid JSON, no markdown."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
            
            response = requests.post(self.deepseek_api_url, headers=headers, json=payload, timeout=45)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    q = json.loads(content[json_start:json_end])
                    if isinstance(q, dict) and q.get("question") and q.get("question") not in asked_texts:
                        return {
                            "question": str(q.get("question", "")).strip(),
                            "type": str(q.get("type", "technical")).strip() or "technical",
                            "difficulty": str(q.get("difficulty", "medium")).strip() or "medium"
                        }
        except Exception as e:
            print(f"❌ DeepSeek API single question error: {e}")
        
        return None

    def _generate_single_with_hf_api(self, job_role, resume_analysis, asked_texts, last_answer):
        """Generate single question using Hugging Face API"""
        try:
            skills_text = ""
            if resume_analysis:
                skills = resume_analysis.get('skills', {})
                skills_list = []
                for category, skill_list in skills.items():
                    skills_list.extend(skill_list)
                skills_text = ", ".join(skills_list[:10])
            
            recent_questions = "\n".join([f"- {t}" for t in asked_texts[-8:]]) if asked_texts else "- (none yet)"
            
            prompt = f"""You are an experienced human interviewer having a natural conversation with a {job_role} candidate.
{f"Candidate skills: {skills_text}" if skills_text else ""}

Previously asked questions (do NOT repeat):
{recent_questions}

{f"Candidate's last answer (for follow-up context): {last_answer[:600]}" if last_answer else ""}

Generate exactly 1 next question that feels like a natural follow-up in a real conversation. Make it sound like you're genuinely interested and building rapport, not just checking boxes.

Examples of conversational questions:
- "That sounds fascinating. What was the most challenging part of that experience for you?"
- "I'm curious - how did you decide to approach that problem?"
- "Based on what you've shared, I'd love to hear more about your experience with..."
- "That's really interesting. Can you tell me about a time when..."

Return ONLY valid JSON (no markdown) in this exact format:
{{"question":"...","type":"technical|behavioral","difficulty":"easy|medium|hard"}}"""

            headers = {
                "Authorization": f"Bearer {self.hf_api_key}",
                "Content-Type": "application/json"
            }
            
            api_endpoint = f"https://api-inference.huggingface.co/models/{self.hf_model}"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 300,
                    "temperature": 0.7,
                    "do_sample": True
                }
            }
            
            response = requests.post(api_endpoint, headers=headers, json=payload, timeout=45)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and result:
                    content = result[0].get('generated_text', '')
                else:
                    content = result.get('generated_text', '') if isinstance(result, dict) else str(result)
                
                # Extract JSON from response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    try:
                        q = json.loads(content[json_start:json_end])
                        if isinstance(q, dict) and q.get("question") and q.get("question") not in asked_texts:
                            return {
                                "question": str(q.get("question", "")).strip(),
                                "type": str(q.get("type", "technical")).strip() or "technical",
                                "difficulty": str(q.get("difficulty", "medium")).strip() or "medium"
                            }
                    except json.JSONDecodeError:
                        pass
            
            return None
            
        except Exception as e:
            print(f"Error in HF single question generation: {e}")
            return None

    def _generate_with_hf_api(self, job_role, resume_analysis, num_questions=3):
        """Generate questions using Hugging Face Inference API"""
        try:
            print(f"🔄 Calling Hugging Face API to generate {num_questions} questions for {job_role}...")
            # Extract skills and experience from resume
            skills_text = ""
            if resume_analysis:
                skills = resume_analysis.get('skills', {})
                skills_list = []
                for category, skill_list in skills.items():
                    skills_list.extend(skill_list)
                skills_text = ", ".join(skills_list[:10])  # Limit to 10 skills
            
            # Create prompt for question generation
            skills_section = f'Based on the candidate\'s background: {skills_text}' if skills_text else ''
            
            prompt = f"""You are an experienced human interviewer conducting a {job_role} interview. Generate exactly {num_questions} questions that feel natural and conversational, like a real interview.

{skills_section}

Create questions that:
- Flow naturally in a conversation
- Build on each other thematically
- Mix personal experience with technical knowledge
- Feel like they're coming from a curious, engaged interviewer
- Vary in depth from introductory to challenging
- Avoid sounding robotic or overly structured

Return questions in JSON format as a list, each with 'question', 'type' (technical/behavioral), and 'difficulty' (easy/medium/hard).

Example of natural questions:
- "I'd love to hear about your journey into {job_role} work. What drew you to this field initially?"
- "That's interesting. Can you walk me through a project where you really had to dig deep into the technical details?"
- "How do you typically approach solving problems when you're not sure where to start?"

Generate exactly {num_questions} conversational questions:"""
            
            # Use Hugging Face Inference API
            headers = {
                "Authorization": f"Bearer {self.hf_api_key}",
                "Content-Type": "application/json"
            }
            
            # Use Hugging Face Inference API endpoint
            # Format: https://api-inference.huggingface.co/models/{model_name}
            api_endpoint = f"https://api-inference.huggingface.co/models/{self.hf_model}"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 1500,  # Increased for more questions
                    "temperature": 0.8,  # Slightly higher for more diversity
                    "return_full_text": False
                }
            }
            
            response = requests.post(
                api_endpoint,
                headers=headers,
                json=payload,
                timeout=60  # Increased timeout for generating more questions
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result[0].get('generated_text', '') if isinstance(result, list) else result.get('generated_text', '')
                
                print(f"✅ Received response from Hugging Face API ({len(generated_text)} characters)")
                
                # Try to parse JSON from the generated text
                try:
                    # Clean up potential markdown formatting
                    clean_text = generated_text.replace('```json', '').replace('```', '').strip()

                    # Extract JSON from the response
                    json_start = clean_text.find('[')
                    json_end = clean_text.rfind(']') + 1
                    if json_start != -1 and json_end > json_start:
                        json_text = clean_text[json_start:json_end]
                        questions = json.loads(json_text)
                        
                        # Validate and format questions
                        formatted_questions = []
                        for q in questions[:num_questions]:
                            if isinstance(q, dict) and 'question' in q:
                                formatted_questions.append({
                                    "question": q.get('question', ''),
                                    "type": q.get('type', 'technical'),
                                    "difficulty": q.get('difficulty', 'medium')
                                })
                        
                        if formatted_questions:
                            print(f"✅ Successfully parsed {len(formatted_questions)} questions from JSON")
                            return formatted_questions
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON parsing failed, trying manual extraction: {e}")
                    # If JSON parsing fails, try to extract questions manually
                    lines = generated_text.split('\n')
                    questions = []
                    seen_questions = set()
                    
                    for line in lines:
                        # Look for question patterns
                        if ('?' in line or 'question' in line.lower()) and len(line.strip()) > 15:
                            # Clean up the line
                            q_text = line.strip().lstrip('- ').lstrip('* ').lstrip('1.').lstrip('2.').lstrip('3.').lstrip('4.').lstrip('5.').strip()
                            
                            # Extract question text
                            if '?' in q_text:
                                q_text = q_text.split('?')[0] + '?'
                            elif 'question' in q_text.lower():
                                # Try to extract question after "question:" or similar
                                parts = q_text.split(':')
                                if len(parts) > 1:
                                    q_text = parts[-1].strip()
                            
                            # Validate and add question
                            if q_text and len(q_text) > 10 and q_text not in seen_questions:
                                seen_questions.add(q_text)
                                
                                # Determine type
                                q_lower = q_text.lower()
                                if any(word in q_lower for word in ['what', 'how', 'explain', 'why', 'which', 'when']):
                                    q_type = "technical"
                                elif any(word in q_lower for word in ['describe', 'tell me', 'share', 'experience', 'time']):
                                    q_type = "behavioral"
                                else:
                                    q_type = "technical"  # Default
                                
                                questions.append({
                                    "question": q_text,
                                    "type": q_type,
                                    "difficulty": "medium"
                                })
                        
                        if len(questions) >= num_questions:
                            break
                    
                    if len(questions) >= 5:  # Return if we got at least 5 questions
                        print(f"✅ Extracted {len(questions)} questions manually")
                        return questions[:num_questions]
            
            elif response.status_code == 503:
                print("⚠️ Hugging Face API model is loading, please wait...")
                # Model might be loading, wait a bit and retry
                import time
                time.sleep(5)
                # Retry once
                return self._generate_with_hf_api(job_role, resume_analysis, num_questions)
            else:
                print(f"❌ Hugging Face API returned status {response.status_code}: {response.text[:200]}")
        
        except requests.exceptions.Timeout:
            print("❌ Hugging Face API request timed out")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error connecting to Hugging Face API: {e}")
        except Exception as e:
            print(f"❌ Error generating questions with Hugging Face API: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def generate_questions(self, job_role, resume_analysis, num_questions=None):
        """
        Generate interview questions based on job role and resume analysis.
        Forces use of local manual questions as per user request, disabling external APIs.
        """
        from config import Config
        
        # Use default if not specified
        if num_questions is None:
            num_questions = Config.DEFAULT_QUESTIONS
        
        # Ensure we generate between 10-15 questions
        num_questions = max(Config.MIN_QUESTIONS, min(Config.MAX_QUESTIONS, num_questions))

        print(f"🔄 Using Local/Manual Question Mode for {job_role}...")
        
        # Skip external API calls entirely and use fallback
        return self.base_questions_fallback(job_role, num_questions)

    def _unused_generate_questions_logic(self, job_role, resume_analysis, num_questions):
        # Original logic preserved but unreachable
        pass
        
        # If we got some questions but not enough, try generating more with different APIs
        all_questions = router_questions or deepseek_questions or hf_questions or []
        if all_questions and len(all_questions) < Config.MIN_QUESTIONS:
            print(f"⚠️ Got {len(all_questions)} questions, need {Config.MIN_QUESTIONS}, generating more...")
            remaining = num_questions - len(all_questions)
            
            # Try to fill remaining with different APIs
            if not router_questions:
                additional = self._generate_with_router_api(job_role, resume_analysis, remaining)
                if additional:
                    all_questions.extend(additional[:remaining])
            
            if len(all_questions) < Config.MIN_QUESTIONS and not deepseek_questions:
                remaining = num_questions - len(all_questions)
                additional = self._generate_with_deepseek_api(job_role, resume_analysis, remaining)
                if additional:
                    all_questions.extend(additional[:remaining])
            
            if len(all_questions) < Config.MIN_QUESTIONS and not hf_questions:
                remaining = num_questions - len(all_questions)
                additional = self._generate_with_hf_api(job_role, resume_analysis, remaining)
                if additional:
                    all_questions.extend(additional[:remaining])
        
        if len(all_questions) >= Config.MIN_QUESTIONS:
            print(f"✅ After additional generation, got {len(all_questions)} questions")
            return all_questions[:num_questions]
        
        # Minimal fallback if all APIs completely fail
        print(f"⚠️ All APIs failed, using minimal fallback for {job_role}")
        return [{
            "question": f"Tell me about yourself and your most relevant experience for this {job_role} role.",
            "type": "behavioral",
            "difficulty": "easy"
        }]
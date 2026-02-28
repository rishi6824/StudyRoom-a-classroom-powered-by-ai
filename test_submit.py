import requests
s = requests.Session()

# 1. Login
r = s.get('http://127.0.0.1:8000/login/')
csrftoken = s.cookies['csrftoken']
login_data = {'username': 'teststudent', 'password': 'pass123', 'csrfmiddlewaretoken': csrftoken}
s.post('http://127.0.0.1:8000/login/', data=login_data)

# 2. Start Interview
csrftoken = s.cookies['csrftoken']
start_data = {'candidate_name': 'Test User', 'csrfmiddlewaretoken': csrftoken}
s.post('http://127.0.0.1:8000/interview/start_with_name/', data=start_data)

# 3. Submit Answer
# Get CSRF for API
s.get('http://127.0.0.1:8000/api/next_question/')
csrftoken = s.cookies['csrftoken']
submit_data = {'answer': 'I am a passionate software engineer with experience in Python and Django.', 'csrfmiddlewaretoken': csrftoken}
r = s.post('http://127.0.0.1:8000/api/submit_answer/', data=submit_data)

print(f"Submit Answer Status: {r.status_code}")
try:
    print(r.json())
except:
    print(r.text[:500])

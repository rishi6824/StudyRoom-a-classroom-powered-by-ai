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

# 3. Get Next Question
r = s.get('http://127.0.0.1:8000/api/next_question/')
print(f"Next Question API Status: {r.status_code}")
try:
    print(r.json())
except:
    print(r.text[:200])

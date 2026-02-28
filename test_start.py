import requests
s = requests.Session()

# Login
r = s.get('http://127.0.0.1:8000/login/')
csrftoken = s.cookies['csrftoken']
login_data = {'username': 'teststudent', 'password': 'pass123', 'csrfmiddlewaretoken': csrftoken}
s.post('http://127.0.0.1:8000/login/', data=login_data)

# Start Interview
csrftoken = s.cookies['csrftoken']
start_data = {'candidate_name': 'Test User', 'csrfmiddlewaretoken': csrftoken}
r = s.post('http://127.0.0.1:8000/interview/start_with_name/', data=start_data)

print(f"Status: {r.status_code}")
try:
    print(r.json())
except:
    print(r.text[:200])

import requests
s = requests.Session()

r = s.get('http://127.0.0.1:8000/login/')
csrftoken = s.cookies['csrftoken']
login_data = {'username': 'teststudent', 'password': 'pass123', 'csrfmiddlewaretoken': csrftoken}
r = s.post('http://127.0.0.1:8000/login/', data=login_data, headers={'Referer': 'http://127.0.0.1:8000/login/'})

r = s.get('http://127.0.0.1:8000/interview/setup/')
print(f"Status Code: {r.status_code}")
if r.status_code == 200:
    print("Page loaded successfully!")
else:
    print(f"Error: {r.status_code}")
    print(r.text[:500])

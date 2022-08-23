import requests
import json
import time
import os
from getpass import getpass

host = 'https://stepik.org'
token = None
headers = None
credentials = None
credentials_path = './stepik_credentials.json'
objects_cache = {}

instructions = """
To get started, do the following (just once):

1. Register and login at https://stepik.org

2. Create OAuth2 keys at https://stepik.org/oauth2/applications

   Select:
   
   * Client type: Confidential
   
   * Authorization grant type: Client credentials
   
3. Enter the created keys (client_id and client_secret)
"""


def input_credentials():
    credentials = {}
    
    print('Enter client_id: ', flush=True)
    credentials['client_id'] = input()
    if credentials['client_id'].strip() == '':
        print('Input cancelled.')
        return None
    
    print('Enter client_secret: ', flush=True)
    credentials['client_secret'] = getpass()
    if credentials['client_secret'].strip() == '':
        print('Input cancelled.')
        return None
    
    return credentials


def load_credentials(credentials_path=None):
    if credentials_path is None:
        credentials_path = globals()['credentials_path']
        
    if not os.path.exists(credentials_path):
        print(instructions, flush=True)
        credentials = input_credentials()
        if credentials is None:
            return None
        with open(credentials_path, 'w') as f:
            json.dump(credentials, f)
        print(f'Saved credentials to {credentials_path}.')
        
    with open(credentials_path, 'r') as f:
        credentials = json.load(f)
        
    return credentials
    

def connect(credentials=None):
    if credentials is None:
        credentials = globals()['credentials']
    if credentials is None:
        credentials = load_credentials()
    if credentials is None:
        return None
    
    auth = requests.auth.HTTPBasicAuth(credentials['client_id'],
                                       credentials['client_secret'])
    
    response = requests.post('https://stepik.org/oauth2/token/',
                             data={'grant_type': 'client_credentials'},
                             auth=auth)

    global token
    token = response.json().get('access_token', None)
    if not token:
        print('Unable to authorize with provided credentials')
        return None
    
    global headers
    headers = {'Authorization': 'Bearer ' + token}

    return token


def ensure_connection(func):
    def wrapper(*args, **kwargs):
        global token
        if token is None:
            connect()
        if token is not None:
            return func(*args, **kwargs)
    return wrapper


@ensure_connection
def fetch(obj_class, obj_id):
    api_url = f'{host}/api/{obj_class}s/{obj_id}'
    response = requests.get(api_url, headers=headers)
    
    if response.status_code != 200:
        raise RuntimeError('Unexpected response: ' + str(response.text))
    
    response = response.json()
    
    
    key = '{}s'.format(obj_class)
    if key not in response:
        raise RuntimeError('Unexpected response' + str(response.text))
    return response[key][0]


@ensure_connection
def fetch_cached(obj_class, obj_id, update_cache=False):
    if obj_class not in objects_cache:
        objects_cache[obj_class] = {}
    if obj_id not in objects_cache[obj_class] or update_cache:
        objects_cache[obj_class][obj_id] = fetch(obj_class, obj_id)
    return objects_cache[obj_class][obj_id]


def is_cached(obj_class, obj_id):
    if obj_class not in objects_cache:
        return False
    if obj_id in objects_cache[obj_class]:
        return True
    return False


@ensure_connection
def update(obj_class, obj):
    api_url = f'{host}/api/{obj_class}s/{obj["id"]}'
    data = {obj_class: obj}
    response = requests.put(api_url, headers=headers, json=data).json()
    key = '{}s'.format(obj_class)
    if key not in response:
        raise RuntimeError('Unexpected response' + str(response.text))
    return response[key][0]


# Inspired by:
# https://github.com/StepicOrg/SubmissionUtility/blob/ac4bd4d7e95a65f51b923b139ea34f1a4cd22c0a/submitter.py

@ensure_connection
def submit(step_id, code, lang='python3.10'):
    api_url = f'{host}/api/attempts/'
    response = requests.post(api_url, headers=headers, json={'attempt': {'step': step_id}})

    result = response.json()
    attempt = result['attempts'][0]
    current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    submission = {
        'time': current_time,
        'reply': {
            'code': code,
            'language': lang
        },
        'attempt': attempt['id']
    }
    api_url = f'{host}/api/submissions'
    response = requests.post(api_url, headers=headers, json={'submission': submission})

    result = response.json()
    
    submission = result['submissions'][0]
    return submission


@ensure_connection
def evaluate(submission_id):
    print('Evaluating...', end='')
    time_out = 0.1
    while True:
        submission = fetch('submission', submission_id)
        status = submission['status']
        hint = submission['hint']
        if status != 'evaluation':
            break
        print('.', end='')
        time.sleep(time_out)
        time_out += time_out
    print(' ', end='')
    print(submission['status'])
    print(submission['hint'])
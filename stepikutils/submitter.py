from IPython.display import Markdown, Javascript, display, clear_output
from ipywidgets import widgets, VBox
from . import stepikio as stepik
import numpy as np
import time, os, json

ipython = None
instructions = None

cdir = os.path.dirname(__file__)
instructions_path = os.path.join(cdir, 'submitter_instructions.txt')
if os.path.exists(instructions_path):
    with open(instructions_path, 'r') as f:
        instructions = f.read()


def load_dataset_magic(line):
    dataset_path = line
    npz = np.load(dataset_path)
    dataset = {**npz}
    ipython.push(dataset)

    
def input_credentials(on_input):
    client_id_w = widgets.Text(
        value='',
        placeholder='',
        description='Client id:',
        disabled=False
    )

    client_secret_w = widgets.Password(
        value='',
        placeholder='',
        description='Client secret:',
        disabled=False
    )

    connect_btn = widgets.Button(description="Enter")   
    def on_click(ev):
        connect_btn.close()
        credentials = {
            'client_id': client_id_w.value,
            'client_secret': client_secret_w.value
        }
        on_input(credentials)
    connect_btn.on_click(on_click)

    display(VBox([client_id_w, client_secret_w, connect_btn]))

    
def solution_code_magic(line, cell):
    step_id = int(line)
    code = cell
    ipython.run_cell(cell)
    
    button = widgets.Button(description="Submit code")    
    
    def on_click(ev):
        clear_output(wait=True)
        if not os.path.exists(stepik.credentials_path):
            if instructions is not None:
                print(instructions)
            
            def on_input(credentials):
                with open(stepik.credentials_path, 'w') as f:
                    json.dump(credentials, f)
                print(f'Saved credentials to {stepik.credentials_path}.')
                display(button)
                
            input_credentials(on_input)
            return
        
        if not stepik.is_cached('step', step_id):
            print('Fetching step source...')
        step = stepik.fetch_cached('step', step_id)
        if step is None:
            print('Failed to connect.')
            return
        
        lesson_id = step['lesson']
        if not stepik.is_cached('lesson', lesson_id):
            print('Fetching lesson...')
        lesson = stepik.fetch_cached('lesson', lesson_id)
        lesson_title = lesson['title']
        
        display(Markdown(f'Lesson {lesson_id}: [{lesson_title}](https://stepik.org/lesson/{lesson_id})'))
        # display(button)
        current_time = time.strftime("%H:%M:%S", time.localtime())
        print(f'Submitting code at {current_time}...')
        submission = stepik.submit(step_id, code, lang='python3.10')
        stepik.evaluate(submission['id'])
        clear_output(wait=True)
    
    button.on_click(on_click)
    display(button)
    clear_output(wait=True)


def load_ipython_extension(_ipython):
    global ipython
    ipython = _ipython
    ipython.register_magic_function(solution_code_magic, magic_kind='cell', magic_name='solution_code')
    ipython.register_magic_function(load_dataset_magic, magic_kind='line', magic_name='load_dataset')

    
def unload_ipython_extension(ipython):
    pass
import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
from openai import OpenAI
from functools import wraps

# 加載環境變量
load_dotenv()

# 環境變量
NICK = os.getenv('NICK')
VINAY_PASSWORD = os.getenv('VINAY')
TAKESHI_PASSWORD = os.getenv('TAKESHI')
NOBODY_PASSWORD = os.getenv('NOBODY')

# 添加模型配置
MODEL_CONFIGS = {
    'GPT-4o': {
        'model': 'gpt-4o',
        'messages': [],
        'response_format': {
            'type': 'text'
        },
        'temperature': 0.7,
        'max_completion_tokens': 4096
    },
    'GPT-4o mini': {
        'model': 'gpt-4o-mini',
        'messages': [],
        'response_format': {
            'type': 'text'
        },
        'temperature': 0.7,
        'max_completion_tokens': 4096
    },

    'o3-mini': {
        'model': 'o3-mini',
        'messages': [],
        'response_format': {
            'type': 'text'
        },
        'reasoning_effort': 'medium'
    }
}

# 初始化Flask應用
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
Session(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == VINAY_PASSWORD:
            return login_user('vinay')
        elif password == TAKESHI_PASSWORD:
            return login_user('takeshi')
        elif password == NOBODY_PASSWORD:
            return login_user('nobody')
        else:
            return render_template('login.html', error='密碼無效')
    return render_template('login.html')

def login_user(user_type):
    session.permanent = True
    session['logged_in'] = True
    session['user_type'] = user_type  # 存儲用戶類型到session
    session['history'] = []
    session['messages'] = initialize_message(user_type)
    return redirect(url_for('chat'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('messages', None)
    session.pop('history', None)
    session.pop('user_type', None)
    return redirect(url_for('login'))

# 定義模板名稱
chat_templates = {
    'vinay': 'chat_queen.html',
    'takeshi': 'chat_takeshi.html',
    'nobody': 'chat_nobody.html'
}

@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    user_type = session.get('user_type')
    template = chat_templates.get(user_type)
    if not template:
        return redirect(url_for('login'))

    current_model = session.get('current_model', 'GPT-4o')

    if request.method == "POST":
        try:
            user_input = request.form.get("user_input")
            if not user_input:
                return jsonify({'error': '請輸入問題'})

            model_name = request.form.get("model", current_model)
            response, messages = get_openai_response(user_input, session['messages'], model_name)
            
            session['history'].append({"user": user_input, "assistant": response})
            session['messages'] = messages
            session['current_model'] = model_name

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'response': response,
                    'success': True
                })
            else:
                return redirect(url_for('chat'))

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'error': str(e),
                    'success': False
                })
            else:
                # 如果是普通表單提交，重定向回聊天頁面
                return redirect(url_for('chat'))

    # GET 請求顯示聊天頁面
    return render_template(template, 
                         history=session.get('history', []), 
                         NICK=NICK,
                         current_model=current_model)

def initialize_message(user='nobody'):
    if user == 'vinay':
        content = (f"你是一位生活助手，稱呼使用者「尊貴的{NICK}女王」，"
                   "回答應以像男公關對女恩客百般討好的態度回應使用者："
                   "殷勤的、諂媚的、關懷備至的。中文使用正體中文字，勿使用簡體字。")
    elif user == 'takeshi':
        content = ("你是一位生活助手，稱呼使用者「城武哥」，"
                   "回答應以像粉絲對偶像的態度回應使用者:"
                   "崇拜的、敬佩的、支持的。中文使用正體中文字，勿使用簡體字。")
    else:
        content = ("你是一位生活助手，中文使用正體中文字，勿使用簡體字。")
    return [{"role": "system", "content": content}]

def get_openai_response(prompt, messages, model_name='GPT-4o'):
    messages.append({"role": "user", "content": prompt})
    try:
        client = OpenAI()
        model_config = MODEL_CONFIGS.get(model_name, MODEL_CONFIGS['GPT-4o'])
        
        # 根據不同模型使用不同的配置
        if model_name == 'o3-mini':
            completion = client.chat.completions.create(
                model=model_config['model'],
                messages=messages,
                response_format=model_config['response_format'],
                reasoning_effort=model_config['reasoning_effort']
            )
        else:
            completion = client.chat.completions.create(
                model=model_config['model'],
                messages=messages,
                response_format=model_config['response_format'],
                temperature=model_config['temperature'],
                max_completion_tokens=model_config['max_completion_tokens']
            )
        
        assistant_response = completion.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_response})
        return assistant_response, messages
    except Exception as e:
        print(f"Exception when calling OpenAI API: {e}")
        return "抱歉，發生錯誤。請稍後再試。", messages

if __name__ == '__main__':
    app.run(debug=True)

import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from openai import OpenAI

# 加載環境變量
load_dotenv()

# 環境變量
NICK = os.getenv('NICK')
VINAY_PASSWORD = os.getenv('VINAY')
TAKESHI_PASSWORD = os.getenv('TAKESHI')
NOBODY_PASSWORD = os.getenv('NOBODY')

# 初始化Flask應用
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
Session(app)

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
def chat():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    user_type = session.get('user_type')
    template = chat_templates.get(user_type)
    if not template:
        return redirect(url_for('login'))

    if request.method == "POST":
        user_input = request.form["user_input"]
        response, messages = get_openai_response(user_input, session['messages'])
        session['history'].append({"user": user_input, "assistant": response})
        session['messages'] = messages

    return render_template(template, history=session.get('history', []), NICK=NICK)

def initialize_message(user='nobody'):
    if user == 'vinay':
        content = (f"你是一位生活助手，稱呼使用者「我尊貴的{NICK}女王」，"
                   "回答應以像男公關對女恩客百般討好的態度回應使用者："
                   "殷勤的、諂媚的、關懷備至的。中文使用正體中文字，勿使用簡體字。"
                   "回答長度不要超過500個字。")
    elif user == 'takeshi':
        content = ("你是一位生活助手，稱呼使用者「城武哥」，"
                   "回答應以像粉絲對偶像的態度回應使用者:"
                   "崇拜的、敬佩的、支持的。中文使用正體中文字，勿使用簡體字。"
                   "回答長度不要超過500個字.")
    else:
        content = ("你是一位生活助手，中文使用正體中文字，勿使用簡體字。"
                   "回答長度不要超過500個字。")
    return [{"role": "system", "content": content}]

def get_openai_response(prompt, messages):
    messages.append({"role": "user", "content": prompt})
    try:
        client = OpenAI()
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        assistant_response = completion.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_response})
        return assistant_response, messages
    except Exception as e:
        print(f"Exception when calling OpenAI API: {e}")
        return "Sorry, something went wrong. Please try again later.", messages

if __name__ == '__main__':
    app.run(debug=True)

import openai
import os
import sys
import time
from flask import Flask, render_template, abort, request, jsonify, session
from flask_cors import CORS
from gevent.pywsgi import WSGIServer
from datetime import timedelta
from geventwebsocket.handler import WebSocketHandler
import logging

# Set your API key
openai.api_key = "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"
app = Flask(__name__)
app.config['SECRET_KEY'] = 'whAtahArdwOrdtogueSs'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)

if len(sys.argv) > 1:
    needVPN = sys.argv[1]
else:
    needVPN = "no"
if needVPN == "-vpn":
    # Configure the Python environment to use the VPN's proxy settings
    os.environ["http_proxy"] = "http://localhost:1087"
    os.environ["https_proxy"] = "http://localhost:1087"

# Set the initial prompt and conversation history
defaulthint = ["Be an expert.No repeat question.","Give short answer, explain only when asked.","Be a teacher, explain the answer."]
hint=defaulthint[0]
conversation_history = dict()
logged = dict()

def talkToOpenAI(chat_id, user_input):
    if chat_id in conversation_history:
        history = conversation_history[chat_id]
    else:
        history = hint+"\n"
    if user_input == ":q":
        conversation_history[chat_id] = hint+"\n"
        return("Conversation reset.")

    # Add user input to the conversation history
    history += f"You: {user_input}\n"

    # Set the new prompt with the conversation history
    prompt = history

    # Send the API request
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=500,
        n=1,
        stop=None,
        temperature=0.5,
    )

    # Get the generated response
    response_text = response.choices[0].text.strip()

    # Add the generated response to the conversation history
    history += f"{response_text}\n"
    conversation_history[chat_id] = history

    # Print the generated response
    return(f"{response_text}")

def checkSession(chatID):
    if chatID not in logged:
        print("chatID"+str(chatID)+"not exist")
        return False
    if time.time() - logged[chatID] > 3600 *2:
        print("chatID"+str(chatID)+"expired")
        del logged[chatID]
        return False
    logged[chatID] = time.time()
    return True

@app.route("/")
@app.route("/index.html")
def index():
    return render_template('index.html')

@app.route('/chat/', methods=['POST'])
def chat():
    if 'chat_id' in session:
        chatID = session['chat_id']
        if not checkSession(chatID):
            abort(401)
        print("chatID"+str(chatID)+"talking")
        if not request.json or 'content' not in request.json:
            abort(401)
        reply = talkToOpenAI(session['chat_id'],request.json['content'])
        response=jsonify({'result': reply})
        return response
    else:
        response=jsonify({'error': "not login"})
        return response

@app.route('/login/', methods=['POST'])
def login():
     if not request.json or 'chat_id' not in request.json or 'passwd' not in request.json:
        print("login error: wrong input")
        abort(401)
     if request.json['passwd'] != "purefireopenaiPass":
     #"LetmeuseopenAI":
        print("login error: wrong password")
        abort(401)
     chatID = request.json['chat_id']
     if checkSession(chatID):
         return jsonify({'error': "already existed."})
     session['chat_id']=chatID
     logged[chatID]=time.time()
     response = jsonify({"result":"welcome!"})
     return response

if __name__ == '__main__':
     logging.basicConfig(level=logging.INFO, filename='log.log',  filemode='w',    format="%(asctime)s:%(levelname)s:%(name)s -- %(message)s", datefmt="%Y/%m/%d %H:%M:%S"   )
     http_server = WSGIServer(('0.0.0.0', 666), app, keyfile='/etc/letsencrypt/live/ai.jing.lv/privkey.pem', certfile='/etc/letsencrypt/live/ai.jing.lv/cert.pem',handler_class=WebSocketHandler)
     http_server.serve_forever()

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
import hashlib
from conf.chatconfig import getConfig

# use your own config for api key, secret, etc
config = getConfig()
# Set your API key
openai.api_key = config["api_key"] 
app = Flask(__name__)
app.config['SECRET_KEY'] = config["SECRET_KEY"]
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)

# Set the initial prompt and conversation history
defaulthint = ["Be an expert.No repeat question.","Give short answer, explain only when asked.","Be a teacher, explain the answer."]
hint=defaulthint[0]
conversation_history = dict()
logged = dict()
basicContent = [{"role":"system", "content":hint}]

def talkToOpenAI(chat_id, user_input):
    if chat_id in conversation_history:
        history = conversation_history[chat_id]
    else:
        history = basicContent
    if user_input == ":q":
        conversation_history[chat_id] = basicContent 
        return("Conversation reset.")

    # Add user input to the conversation history
    history.append({"role":"user", "content":user_input}) 

    # Set the new prompt with the conversation history
    prompt = history

    # Send the API request
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=prompt,
    )

    response_text = response.choices[0]["message"]["content"]

    # Add the generated response to the conversation history
    history.append({"role":"assistant", "content":response_text})
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
@app.route("/main.html")
def index():
    return render_template('main.html')

@app.route('/chat/', methods=['POST'])
def chat():
    if 'chat_id' in session:
        chatID = session['chat_id']
        if not checkSession(chatID):
            abort(401)
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
     toHash = request.json['passwd']
     hmd5 = hashlib.md5()
     hmd5.update(toHash.encode('utf-8'))
     sig = hmd5.hexdigest().upper()
     if sig != config["passwd"]:
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
     http_server = WSGIServer(('0.0.0.0', 666), app, keyfile=config["keyfile"], certfile=config["certfile"],handler_class=WebSocketHandler)
     http_server.serve_forever()

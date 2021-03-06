from __future__ import unicode_literals
import time
from datetime import datetime
import random

import json

from flask import Flask
from flask import render_template, jsonify, request
app = Flask(__name__)
app.config['APPLICATION_ROOT'] = '/randomizer'

@app.template_filter('datetime')
def datetime_format(value, format='%Y-%m-%d  %H:%M'):
    if not value: return "-"
    if isinstance(value, unicode): return value
    if isinstance(value, int): value = datetime.fromtimestamp(value)
    return value.strftime(format)

global debug
debug = False

from git import *
repo = Repo(".")
assert repo.bare == False

import randomizer

games_json = {}
for game in randomizer.randomizer_games:
    game_json = {}
    game_json['name'] = game.name
    game_json['options'] = {} #game.options
    game_json['presets'] = game.presets #game.options
    games_json[game.identifier] = game_json

games_json = json.dumps(games_json)
    
cooldowns = {}

@app.route('/generate', methods=["POST"])
def generate():
    # For some reason, in case we've never touched the request, outgoing JSON
    # replies (such as a cooldown one) send zero-byte replies.  This only
    # happens on the deployed uWSGI server and not Flask's internal debugging
    # one.
    request.form.get('randomizer') 
    
    ip = request.remote_addr
    if ip in cooldowns and time.time() < cooldowns[ip] + 60:
        return jsonify({'error': 'cooldown', 'cooldown': (cooldowns[ip] + 60) - time.time()})
    if len(request.form.get('filename')) > 64:
        return jsonify({'error': 'filename'})
    
    starttime = time.time()
    gameid = request.form.get('game')
    for g in randomizer.randomizer_games:
        #print g.identifier, gameid
        if g.identifier == gameid:
            Game = g
    
    game = Game()
    form = game.Form(request.form)
    for field in form:
        game.choices[field.name] = field.data
    filename = game.produce(filename=request.form.get('filename'), debug=debug)
    
    endtime = time.time()
    cooldowns[ip] = endtime
    
    timedelta = time.time() - starttime
    return jsonify({'filename': filename, 'time': timedelta})
    

@app.route("/")
def index():
    all_commits = repo.iter_commits('master')
    commits = []
    for commit in all_commits:
        if not commit.message.startswith('Merge '):
            commits.append(commit)
        if len(commits) == 10: break
    
    return render_template("index.html", games=randomizer.randomizer_games, games_json=games_json, debug=debug, randlogo=random.randint(1, 28), commits=commits)

if __name__ == "__main__":
    print "Running..."
    debug = True
    app.run(host="", port=8580, debug=True, threaded=True, use_evalex=False)

if not app.debug:
    import logging
    file_handler = logging.FileHandler('flask.log')
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

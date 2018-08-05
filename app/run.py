# all the imports
import os
import sqlite3
from flask import Flask, request, g, \
     render_template, flash, send_from_directory
from werkzeug.utils import secure_filename
import logging
import json
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

with open(os.path.join(app.root_path, 'config.json')) as f:
    config = json.load(f)

app.config.update(config)
# TODO: make sure the download dialog is scrollable


class DictNoNone(dict):
    def __setitem__(self, key, value):
        if value is not None:
            dict.__setitem__(self, key, value)


database = app.config['DATABASE']
if os.environ.get('DB'):
    database = os.path.join(app.root_path, os.environ.get('DB'))

d = DictNoNone()
d['DATABASE']=database
d['SECRET_KEY']=os.environ.get('secretKey')
d['USERNAME']=os.environ.get('username')
d['PASSWORD']=os.environ.get('password')
d['UPLOAD_FOLDER']=os.environ.get('uploadFolder')
# TODO: test to see if env vars overwrite config in json
app.config.update(d)
app.config.from_envvar('ELEMENT_TO_CLASS_SETTINGS', silent=True)

handler = RotatingFileHandler('error.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)


def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


def get_page_text():
    init_page_text_if_none()
    db = get_db()
    lang = get_lang()
    cur = db.execute('select "text" from PageText order by id desc')
    return cur.fetchall()


def get_lang():
    default_lang = 'EN-US'
    if request is None or request.accept_languages is None \
            or request.accept_languages[0] is None \
            or request.accept_languages[0][0] is None:
        return default_lang
    clean_lang = str(request.accept_languages[0][0]).upper().strip()
    if clean_lang.count is 0:
        return default_lang
    # TODO: see if language is being used


@app.cli.command('initdb')
def initdb_command():
    init_db()
    print('Initialized the database.')


def init_page_text_if_none():
    db = get_db()
    cur = db.execute('select "text" from PageText limit 1')
    if cur.fetchone() is None:
        with app.open_resource('init_page_text.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


@app.route('/')
def convert_css():
    page_text = get_page_text()
    return render_template('convert_css.html', page_text=page_text)


def get_unique_class_name(class_name, used_class_names, dup_count):
    if dup_count:
        dup_count += 1
        new_class_name = class_name + '_' + str(dup_count)
    else:
        new_class_name = class_name
    if new_class_name in used_class_names:
        if not dup_count:
            dup_count = 1
        return get_unique_class_name(class_name, used_class_names, dup_count)
    return new_class_name


def get_new_line(line, line_num, used_class_names, element_to_class_str, lines_that_changed):
    new_line = line
    lstrip_line = line.lstrip()
    styles = lstrip_line.split('{', 1)[1]
    styles_on = lstrip_line.split('{', 1)[0].replace(' ', '').replace(',', '_')
    class_or_ele = get_unique_class_name(styles_on, used_class_names, 0)
    if lstrip_line and lstrip_line[0] not in ['.', '#']:
        if lstrip_line.startswith(':root'):
            new_class = element_to_class_str + 'root'
        elif lstrip_line[0] == '*':
            new_class = '.' + element_to_class_str + 'all_elements'
        else:
            new_class = element_to_class_str + styles_on
        lines_that_changed.append(line_num)
        class_or_ele = get_unique_class_name(new_class, used_class_names, 0)
        new_line = class_or_ele
        if "{" in line:
            new_line += ' {' + styles
    return [new_line, class_or_ele]


@app.route('/upload_css', methods=['POST'])
def upload_css():
    can_upload = True
    if 'css_file' not in request.files:
        error_message = 'CSS file was not submitted'
        flash(error_message)
        app.logger.error(error_message)
        result = ''
    elif request.method != 'POST':
        error_message = 'HTTP POST only'
        app.logger.error(error_message)
        flash(error_message)
        result = ''
    if can_upload:
        css_file = request.files['css_file']
        filename = secure_filename(css_file.filename)
        new_filename = 'new_' + filename
        print(app.config['USERNAME'])

        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        old_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        css_file.save(old_file)

        lines_that_changed = []
        used_class_names = []
        element_to_class_str = '.element_to_class_'
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
        new_file = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        with open(new_file, 'w') as out_file, open(old_file, 'r') as in_file:
            new_file_text = ''
            for line_num, line in enumerate(in_file):
                new_line = line
                lstrip_line = line.lstrip()
                if len(lstrip_line.split('{', 1)) > 1:
                    new_line, class_or_ele = get_new_line(line, line_num, used_class_names, element_to_class_str, lines_that_changed)
                    used_class_names.append(class_or_ele)
                new_file_text += new_line
            out_file.write(new_file_text)
        if not lines_that_changed:
            flash_message = 'No changes made'
        elif len(lines_that_changed) == 1:
            flash_message = 'Line changed: ' + str(lines_that_changed[0])
        else:
            last_line_number_changed = lines_that_changed.pop()
            flash_message = 'Lines changed: '
            flash_message += ', '.join(str(x) for x in lines_that_changed)
            flash_message += ' and ' + str(last_line_number_changed)
        flash(flash_message)
        result = new_filename
    page_text = get_page_text()
    return render_template('convert_css.html', page_text=page_text, filename=result)


@app.route('/download_css/<filename>', methods=['GET'])
def download_css(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename=filename)


# all the imports
import os
import sqlite3
from flask import Flask, request, g, \
     render_template, flash, send_from_directory
from werkzeug.utils import secure_filename
import logging
from logging.handlers import RotatingFileHandler

UPLOAD_FOLDER = os.environ['uploadFolder']

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, os.environ['DB']),
    SECRET_KEY=os.environ['secretKey'],
    USERNAME=os.environ['username'],
    PASSWORD=os.environ['password']
))
app.config.from_envvar('ELEMENT_TO_CLASS_SETTINGS', silent=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

handler = RotatingFileHandler('debug.log', maxBytes=10000, backupCount=1)
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


def get_main_page_text():
    db = get_db()
    cur = db.execute('select "text" from PageText order by id desc')
    return cur.fetchall()


@app.cli.command('initdb')
def initdb_command():
    init_db()
    print('Initialized the database.')


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
    page_text = get_main_page_text()
    return render_template('convert_css.html', page_text=page_text)


def get_unique_class_name(class_name, used_class_names, dup_count):
    if dup_count:
        dup_count += 1
        new_class_name = class_name + '_' + str(dup_count)
    else:
        new_class_name = class_name
    app.logger.error(new_class_name)
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
        flash('CSS file was not submitted')
        result = ''
    elif request.method != 'POST':
        flash('HTTP POST only')
        result = ''
    if can_upload:
        file = request.files['css_file']
        filename = secure_filename(file.filename)
        new_filename = 'new_' + filename

        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        old_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(old_file)

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
    page_text = get_main_page_text()
    return render_template('convert_css.html', page_text=page_text, filename=result)


@app.route('/download_css/<filename>', methods=['GET'])
def download_css(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename=filename)


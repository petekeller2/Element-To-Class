# About

This application is used to move
 CSS styles off of elements and onto
 classes. One reason why you would
 want to do this is to avoid a conflict
 of styles on elements. Example: You
 put styles directly on an element and
 then use a library that also does
 this.

# Setup

1. Create a venv environment named venv
2. `export FLASK_APP=app/run.py`
3. `. venv/bin/activate`
4. Update app/config.json or the config 
environment variables
5. `flask initdb`
6. `flask run`
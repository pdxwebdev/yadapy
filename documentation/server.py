from flask import Flask, render_template, request, redirect, url_for
from wtforms import Form, TextAreaField, TextField
from pymongo import Connection
import pymongo

app = Flask(__name__)

class StepForm(Form):
    title = TextField('Title')
    desc = TextField('Description')
    obj = TextAreaField('Object')
    ref = TextField('Parent')
    order = TextField('Order')

@app.route('/edit/', methods=['GET', 'POST'])
def edit():
    con = Connection('localhost')
    if request.method == 'POST':
        con.standard.docs.insert({
            'title': request.form['title'],
            'desc': request.form['desc'],
            'ref': request.form['ref'],
            'order': int(request.form['order']),
            'obj': request.form['obj'].strip()
        })
        return redirect(url_for('edit'))
    elif request.method == 'GET':
        form = StepForm()
        steps = con.standard.docs.find().sort("order", pymongo.ASCENDING)
        
        return render_template('edit.html', form=form, steps=steps)

if __name__ == '__main__':
    app.run(debug=True)
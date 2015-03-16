from flask import Flask, render_template, request, redirect, url_for
from wtforms import Form, TextAreaField, TextField
from pymongo import Connection
import pymongo
from operator import itemgetter

app = Flask(__name__)

class StepForm(Form):
    title = TextField('Title')
    desc = TextField('Description')
    obj = TextAreaField('Object')
    ref = TextField('Parent')
    order = TextField('Order')
    page = TextField('Page')

@app.route('/page/<page>/')
def docs(page):
    con = Connection('localhost')
    steps = con.standard.docs.find({"page": page, "component": "step"}).sort("order", pymongo.ASCENDING)
    res = con.standard.docs.find({"page": page, "component": "description"})
    desc = res[0] if res.count() > 0 else None
    return render_template('docs.html', steps=steps, page=page, desc=desc)

@app.route('/edit/', methods=['GET', 'POST'])
def edit():
    con = Connection('localhost')
    if request.method == 'POST':
        con.standard.docs.insert({
            'title': request.form['title'],
            'desc': request.form['desc'],
            'ref': request.form['ref'],
            'order': int(request.form['order']),
            'obj': request.form['obj'].strip(),
            'page': request.form['page'],
            'component': 'step'
        })
        return redirect(url_for('edit'))
    elif request.method == 'GET':
        form = StepForm()
        steps = con.standard.docs.find().sort("order", pymongo.ASCENDING)
        return render_template('edit.html', form=form, steps=steps)

if __name__ == '__main__':
    app.run(debug=True)
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

@app.route('/')
def docs():
    con = Connection('localhost')
    steps = con.standard.docs.find().sort("order", pymongo.ASCENDING)
    steps_dict = {}
    for step in steps:
        if step['ref']:
            if 'substeps' not in steps_dict[step['ref']]:
                steps_dict[step['ref']]['substeps'] = []
            steps_dict[step['ref']]['substeps'].append(step)
        else:
            steps_dict[str(step['_id'])] = step
    newlist = sorted([step for x, step in steps_dict.items()], key=itemgetter('order')) 
    return render_template('docs.html', steps=newlist)

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
        steps_dict = {}
        for step in steps:
            if step['ref']:
                if 'substeps' not in steps_dict[step['ref']]:
                    steps_dict[step['ref']]['substeps'] = []
                steps_dict[step['ref']]['substeps'].append(step)
            else:
                steps_dict[str(step['_id'])] = step
        newlist = sorted([step for x, step in steps_dict.items()], key=itemgetter('order')) 
        return render_template('edit.html', form=form, steps=newlist)

if __name__ == '__main__':
    app.run(debug=True)
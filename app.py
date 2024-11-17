from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import xml.etree.ElementTree as ET
import os
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class MessageType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    endpoint = db.Column(db.String(150), nullable=False, default="http://localhost:8080/validator")
    # Relationships
    test_messages = db.relationship('TestMessage', backref='message_type', lazy=True)
    transforms = db.relationship('XSLTransform', backref='message_type', lazy=True)

class TestMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    message_content = db.Column(db.Text, nullable=False)
    message_type_id = db.Column(db.Integer, db.ForeignKey('message_type.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ResponseMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_message_id = db.Column(db.Integer, db.ForeignKey('test_message.id'))
    response_content = db.Column(db.Text)  # XML stored as text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class XSLTransform(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    transform_content = db.Column(db.Text, nullable=False)
    message_type_id = db.Column(db.Integer, db.ForeignKey('message_type.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

####
####  Message Types
####
@app.route('/api/message_types/<int:id>/edit', methods=['GET'])
def edit_message_type_form(id):
    type = MessageType.query.get_or_404(id)
    return render_template('message_types/_edit.html', type=type)

@app.route('/api/message_types/<int:id>', methods=['PUT', 'PATCH'])
def update_message_type(id):
    try:
        type = MessageType.query.get_or_404(id)
        type.name = request.form['name']
        type.description = request.form['description']
        type.endpoint = request.form['endpoint']
        
        db.session.commit()
        
        return f'<p>Updated</p>'
    except Exception as e:
        db.session.rollback()
        return str(e), 400
    
@app.route('/api/message_types', methods=['POST'])
def create_message_type():
    try:
        # Create message type
        type = MessageType(
            name=request.form['name'],
            description=request.form['description'],
            endpoint=request.form['endpoint']
        )
        db.session.add(type)
        db.session.commit()
        message = "Success"
        return render_template('_good_alert.html', message=message)
    except Exception as e:
        print("Error:", str(e))
        return str(e), 400

@app.route('/get_message_types')
def get_message_types():
    types = MessageType.query.all()
    return render_template('message_types/_list.html', message_types=types)

@app.route('/api/message_types/<int:id>', methods=['DELETE'])
def delete_message_type(id):
    try:
        type = MessageType.query.get_or_404(id)
        db.session.delete(type)
        db.session.commit()
        return '', 204
    except Exception as e:
        return str(e), 400
    
#@app.route('/partials/endpoint-input')
#def endpoint_input():
#    return render_template('message_types/_endpoint_input.html')

@app.route('/get_message_types_options')
def get_message_types_options():
    message_types = MessageType.query.all()
    return render_template('message_types/_options.html', message_types=message_types)

####
####  Messages 
####
@app.route('/get_test_messages')
def get_test_messages():
    test_messages = TestMessage.query.order_by(TestMessage.created_at.desc()).all()
    return render_template('messages/_list.html', test_messages=test_messages)


@app.route('/api/messages', methods=['POST'])
def create_message():
    try:
        message = TestMessage(
            name=request.form['name'],
            description=request.form['description'],
            message_content=request.form['content'],
            message_type_id=request.form['message_type_id']
        )
        db.session.add(message)
        db.session.commit()
        message = "Success"
        return render_template('_good_alert.html', message=message)
    except Exception as e:
        print("Error:", str(e))
        return str(e), 400
    
@app.route('/api/messages/<int:id>', methods=['GET'])
def get_message(id):
    print("---------------")
    message = TestMessage.query.get_or_404(id)
    return render_template('messages/_detail.html', message=message)

@app.route('/api/messages/<int:id>', methods=['DELETE'])
def delete_message(id):
    try:
        message = TestMessage.query.get_or_404(id)
        db.session.delete(message)
        db.session.commit()
        return '', 204
    except Exception as e:
        return str(e), 400

# Messages sending to endpoint
@app.route('/api/messages/<int:id>/send', methods=['POST'])
def send_message(id):
    try:
        message = TestMessage.query.get_or_404(id)
        endpoint = message.message_type.endpoint
        results = []
        try:
            # Send the message content to the endpoint
            response = requests.post(
                endpoint,
                data=message.message_content,
                headers={'Content-Type': 'application/json'},
                timeout=10  # 10 second timeout
            )
            print(response.text)
            results.append({
                'endpoint': endpoint,
                'status': response.status_code,
                'response': response.text
            })
        except request.exceptions.RequestException as e:
            results.append({
                'endpoint': endpoint,
                'status': 'error',
                'error': str(e)
            })

        return render_template('responses/_view.html', message=results[0]) 
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    
####
####  Responses 
####
@app.route('/api/responses', methods=['POST'])
def create_response():
    data = request.json
    response = ResponseMessage(
        test_message_id=data['message_id'],
        response_content=data['content']
    )
    db.session.add(response)
    db.session.commit()
    return render_template('responses/_row.html', response=response)

####
####  Transforms 
####
@app.route('/get_transforms')
def get_transforms():
    transforms = XSLTransform.query.order_by(XSLTransform.created_at.desc()).all()
    return render_template('transforms/_list.html', transforms=transforms)

@app.route('/api/transforms', methods=['POST'])
def create_transform():
    try:
        transform = XSLTransform(
            name=request.form.get("name"),
            transform_content=request.form.get("content"),
            message_type_id=request.form.get("message_type_id")
        )
        db.session.add(transform)
        db.session.commit()
        message = "Success"
        return render_template('_good_alert.html', message=message)
    except Exception as e:
        print("Error:", str(e))
        return str(e), 400
    
@app.route('/api/transform/<int:id>', methods=['GET'])
def get_transform(id):
    transform = XSLTransform.query.get_or_404(id)
    return render_template('transforms/_detail.html', transform=transform)

# Get transform by Message Type (should only allow 1)
# curl "127.0.0.1:5000/api/xsl?name=Patient"
@app.route('/api/xsl', methods=['GET'])
def get_transform_by_name():
    name = request.args.get("name")
    message_type = MessageType.query.filter_by(name=name).first()
    transforms = message_type.transforms if message_type else []
    if transforms:
        return transforms[0].transform_content
    abort(404)

@app.route('/api/transform/<int:id>', methods=['DELETE'])
def delete_transform(id):
    try:
        transform = XSLTransform.query.get_or_404(id)
        db.session.delete(transform)
        db.session.commit()
        return '', 204
    except Exception as e:
        return str(e), 400
    
@app.route('/')
def index():
    message_types = MessageType.query.all()
    test_messages = TestMessage.query.all()  # Add this line
    return render_template('index.html', 
                         message_types=message_types,
                         test_messages=test_messages)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port="5500", debug=True)
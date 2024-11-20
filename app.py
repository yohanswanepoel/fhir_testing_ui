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
    # Relationsships
    response = db.relationship('ResponseMessage',backref='message', lazy=True)


class ResponseMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_message_id = db.Column(db.Integer, db.ForeignKey('test_message.id'))
    response_content = db.Column(db.Text)  # XML stored as text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    

class XSLTransform(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    transform_content = db.Column(db.Text, nullable=False)
    direction = db.Column(db.String(3), nullable=True, default='c2f')
    message_type_id = db.Column(db.Integer, db.ForeignKey('message_type.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

####
####  Message Types
####
@app.route('/api/message_types/<int:id>/edit', methods=['GET'])
def edit_message_type_form(id):
    type = MessageType.query.get_or_404(id)
    return render_template('message_types/_edit.html', type=type)

@app.route('/api/message_types/<int:id>', methods=['POST'])
def update_message_type(id):
    try:
        type = MessageType.query.get_or_404(id)
        type.name = request.form['name']
        type.description = request.form['description']
        type.endpoint = request.form['endpoint']
        message = "Success"
        db.session.commit()
        #return render_template('_good_alert.html', message=message)
        return redirect('/static/message_types/admin.html')
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
        return redirect('/static/message_types/admin.html')
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
        return '', 200
    except Exception as e:
        return str(e), 400
    
#@app.route('/partials/endpoint-input')
#def endpoint_input():
#    return render_template('message_types/_endpoint_input.html')

@app.route('/get_message_types_options')
def get_message_types_options():
    message_types = MessageType.query.all()
    return render_template('message_types/_options.html', message_types=message_types)

@app.route('/get_cda_messages')
def get_cda_messages():
    messages = ResponseMessage.query.all()
    return render_template('responses/_options.html', messages=messages)

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
        return redirect('/static/messages/admin.html')
        #return render_template('_good_alert.html', message=message)
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
        return '', 200
    except Exception as e:
        return str(e), 400

# Messages sending to endpoint
@app.route('/api/messages/<int:id>/send', methods=['POST'])
def send_message(id):
    toFhir = request.args.get('toFHIR')
    try:
        message = TestMessage.query.get_or_404(id)
        endpoint = message.message_type.endpoint
        emrStatus = 'gray'
        toFHIR = "n"
        fhirColour = "gray"
        validationStatus = "gray"
        validationColour = "gray"
        transformationColour = "gray" 
        transformStore = "gray"
        transformStatus = "gray"
        fhirStatus = "gray"
        emrColour = "#4a90e2"
        cdaStore = "gray"
        cdaStoreStatus = "gray"
        if toFhir:
            endpoint = f"{endpoint}?toFHIR=Y"
            toFHIR = "y"
        results = []
        try:
            # Send the message content to the endpoint
            response = requests.post(
                endpoint,
                data=message.message_content,
                headers={'Content-Type': 'application/json',
                         'X-test-message-id': f'{id}'},
                timeout=10  # 10 second timeout
            )
            #print(response.headers)
            emrStatus = 'green'
            validationColour = '#50b068'
            if 'validation-passed' in response.headers:
                validationResult = response.headers['validation-passed']
                if validationResult == "true":
                    validationStatus = "green"
                else:
                    validationStatus = "red"
            if 'message_transformed' in response.headers:
                transformStatus = "green"
                transformationColour = "#50b068"
                transformStore = "#9b59b6"
                cdaStore = "#9b59b6"
                if 'message_stored_cda' in response.headers:
                    cdaStoreStatus = "green"
                else:
                    cdaStoreStatus = "red"
            if toFhir and 'validation-passed' in response.headers:
                fhirColour = "#e6a843"
                if 'fhir_updated' in response.headers:
                    fhirStatus = "green"
                else:
                    fhirStatus = "red"
            results.append({
                'endpoint': endpoint,
                'toFHIR': toFHIR,
                'status': response.status_code,
                'response': response.text,
                'emrStatus': emrStatus,
                'fhirColour': fhirColour,
                'validationColour': validationColour,
                'validationStatus': validationStatus,
                'transformationColour': transformationColour,
                'transformStore': transformStore,
                'transformStatus': transformStatus,
                'fhirStatus': fhirStatus,
                'emrColour': emrColour,
                'cdaStore': cdaStore,
                'cdaStoreStatus': cdaStoreStatus
            })
            
        except requests.exceptions.RequestException as e:
            print("Exception section")
            emrStatus = 'red'
            results.append({
                'endpoint': endpoint,
                'status': 'Error',
                'response': str(e),
                'emrStatus': emrStatus,
                'fhirColour': fhirColour,
                'validationColour': validationColour,
                'validationStatus': validationStatus,
                'transformationColour': transformationColour,
                'transformStore': transformStore,
                'transformStatus': transformStatus,
                'fhirStatus': fhirStatus,
                'emrColour': emrColour,
                'cdaStore': cdaStore,
                'cdaStoreStatus': cdaStoreStatus
            })
        return render_template('responses/_view_with_graph.html', message=results[0]) 
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    
####
####  Responses 
####

@app.route('/cda_system/<int:id>', methods=['GET'])
def get_cda_response(id):
    message = ResponseMessage.query.get_or_404(id)
    return message.response_content

@app.route('/api/responses/<int:id>', methods=['GET'])
def get_response(id):
    message = ResponseMessage.query.get_or_404(id)
    return render_template('responses/_view.html', message=message)

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

@app.route('/get_responses', methods=['GET'])
def get_all_responses():
    messages = ResponseMessage.query.order_by(ResponseMessage.created_at.desc()).all()
    return render_template('responses/_list.html', messages=messages)

@app.route('/api/clear_responses', methods=['GET'])
def clear_all_responses():
    print("....DELETE ALL MESSAGES....")
    ResponseMessage.query.delete()
    db.session.commit()
    return redirect('/static/responses/admin.html')

@app.route('/api/run_all_tests', methods=['GET'])
def run_all_tests():
    #messages = ResponseMessage.query.order_by(ResponseMessage.created_at.desc()).all()
    #TO DO Run All tests
    return redirect('/static/responses/admin.html')

###
###  Test Responses - save the CDA message
###

@app.route('/cda_system', methods=['POST'])
def store_test_result():
    data = request.data 
    if 'X-test-message-id' in request.headers:
        message_id = request.headers['X-test-message-id']
    else:
        return '',404
    test_message_id = int(message_id)
    response = ResponseMessage(
        test_message_id=test_message_id,
        response_content=request.data 
    )
    db.session.add(response)
    db.session.commit()
    return 'success',200


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
        return redirect("/static/transforms/admin.html")
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
    direction = request.args.get("direction")
    message_type = MessageType.query.filter_by(name=name).first()
    transforms = message_type.transforms if message_type else []
    for transform in transforms:
        if transform.direction == direction:
            return transform.transform_content
    abort(404)

@app.route('/api/transform/<int:id>', methods=['DELETE'])
def delete_transform(id):
    try:
        transform = XSLTransform.query.get_or_404(id)
        db.session.delete(transform)
        db.session.commit()
        return '', 200
    except Exception as e:
        return str(e), 400
    

@app.route('/queryFHIR2CDA', methods=['POST'])
def query_CDE():
    camel_host = os.environ.get('CAMEL_HOST',"http://localhost:8080")
    testId = request.form['test_message_id']
    response_message = ResponseMessage.query.get_or_404(testId)
    content = response_message.response_content
    id = response_message.message.id
    object = response_message.message.message_type.name
    endpoint = f'{camel_host}/queryFHIRfromCDA/{object}/{id}'
    try:
        response = requests.post(
            endpoint,
            headers={'Content-Type': 'application/json',
                        'X-test-message-id': f'{id}'},
            timeout=10  # 10 second timeout
        )
        message = {}
        message['response'] = response.status_code
        message['content'] = response.text
        return render_template('queries/_view.html', message=message)
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
    app.run(host="0.0.0.0", debug=True)
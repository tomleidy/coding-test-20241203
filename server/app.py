"""
Coding Test: Contacts CRUD
By: Tom Leidy + Claude 3.5 Sonnet

"""

from datetime import datetime, timezone
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import bleach


NAME_FIELD_SIZE = 50
EMAIL_FIELD_SIZE = 120
SQL_REGEX = r"(?i)(;|--|\b(drop|select|insert|delete|update|alter|create|truncate)\b)"


def sanitize_input(input_string):
    sanitized = bleach.clean(input_string)
    # check for SQL injections, just in case
    if re.search(SQL_REGEX, sanitized):
        raise ValueError("Invalid input detected")
    return sanitized


def is_valid_email(email):
    email_regex = r'^[^@]+@[^@]+\.[^@]+$'
    return re.match(email_regex, email) is not None


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*",
     "methods": ["GET", "POST", "PUT", "DELETE"], "allow_headers": ["Content-Type"]}})
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contacts.db'
db = SQLAlchemy(app)


class TimeNow:
    def __call__(self):
        return datetime.now(timezone.utc)


timenow = TimeNow()


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(NAME_FIELD_SIZE), nullable=False)
    last_name = db.Column(db.String(NAME_FIELD_SIZE), nullable=False)
    created_at = db.Column(db.DateTime, default=timenow)
    updated_at = db.Column(db.DateTime, default=timenow, onupdate=timenow)
    emails = db.relationship('Email', backref='contact', lazy=True, cascade='all, delete-orphan')


class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(EMAIL_FIELD_SIZE), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)


@app.route('/')
def serve_app():
    return send_from_directory('static', 'index.html')


@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename)


@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('static/css', filename)


with app.app_context():
    db.create_all()


@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    contacts = Contact.query.all()
    return jsonify([{
        'id': c.id,
        'firstName': c.first_name,
        'lastName': c.last_name,
        'emails': [{'id': e.id, 'email': e.email} for e in c.emails],
        'createdAt': c.created_at.isoformat(),
        'updatedAt': c.updated_at.isoformat()
    } for c in contacts])


@app.route('/api/contacts/<int:contact_id>', methods=['GET'])
def get_contact(contact_id):
    contact = db.session.get(Contact, contact_id)
    if contact is None:
        return jsonify({'error': 'Contact not found'}), 404
    return jsonify({
        'id': contact.id,
        'firstName': contact.first_name,
        'lastName': contact.last_name,
        'emails': [{'id': e.id, 'email': e.email} for e in contact.emails],
        'createdAt': contact.created_at.isoformat(),
        'updatedAt': contact.updated_at.isoformat()
    })


@app.route('/api/contacts', methods=['POST'])
def create_contact():
    data = request.get_json()

    try:
        if not data.get('firstName') or not data.get('lastName'):
            raise ValueError("First name and last name are required")

        if len(data['firstName']) > NAME_FIELD_SIZE or len(data['lastName']) > NAME_FIELD_SIZE:
            raise ValueError("First name or last name is too long")

        contact = Contact(
            first_name=sanitize_input(data['firstName']),
            last_name=sanitize_input(data['lastName'])
        )

        for email_data in data.get('emails', []):
            if len(email_data['email']) > EMAIL_FIELD_SIZE:
                raise ValueError(f"Email is too long: {email_data['email']}")
            if not is_valid_email(email_data['email']):
                raise ValueError(f"Invalid email format: {email_data['email']}")
            contact.emails.append(Email(email=sanitize_input(email_data['email'])))

        db.session.add(contact)
        db.session.commit()

        return jsonify({
            'id': contact.id,
            'firstName': contact.first_name,
            'lastName': contact.last_name,
            'emails': [{'id': e.id, 'email': e.email} for e in contact.emails],
            'createdAt': contact.created_at.isoformat(),
            'updatedAt': contact.updated_at.isoformat()
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id):
    contact = db.session.get(Contact, contact_id)
    if contact is None:
        return jsonify({'error': 'Contact not found'}), 404
    data = request.get_json()

    if not data.get('firstName') or not data.get('lastName'):
        return jsonify({'error': 'First name and last name are required'}), 400

    contact.first_name = sanitize_input(data['firstName'])
    contact.last_name = sanitize_input(data['lastName'])

    # Remove existing emails
    Email.query.filter_by(contact_id=contact.id).delete()

    # Add new emails
    for email_data in data.get('emails', []):
        if len(email_data['email']) > 120:
            return jsonify({'error': f"Email is too long: {email_data['email']}"}), 400
        if not is_valid_email(email_data['email']):
            return jsonify({'error': f"Invalid email format: {email_data['email']}"}), 400
        email = Email(email=sanitize_input(email_data['email']))
        contact.emails.append(email)

    db.session.commit()

    return jsonify({
        'id': contact.id,
        'firstName': contact.first_name,
        'lastName': contact.last_name,
        'emails': [{'id': e.id, 'email': e.email} for e in contact.emails],
        'createdAt': contact.created_at.isoformat(),
        'updatedAt': contact.updated_at.isoformat()
    })


@app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    contact = db.session.get(Contact, contact_id)
    if contact is None:
        return jsonify({'error': 'Contact not found'}), 404
    db.session.delete(contact)
    db.session.commit()
    return '', 204


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

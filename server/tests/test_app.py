"""
Integration and unit tests for the Contacts API.

This module contains a series of tests designed to verify the functionality,
security, and edge case handling of the Contacts API. It includes tests for
CRUD operations, validation logic, error handling, and security measures
like protection against SQL injection, XSS attacks, and excessively long inputs.

Fixtures:
    client: Provides a Flask test client with an isolated database for testing.

Test Cases:
    - Contact creation, retrieval, updating, and deletion.
    - Input validation for required fields, email formats, and field length limits.
    - Security against SQL injection and XSS.
    - CORS header verification.
"""


import pytest
from ..app import app, db, Contact, Email  # pylint: disable=W0611

# pylint: disable=W0621


@pytest.fixture
def client():
    """Set up and provide a test client with an isolated test database."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


def test_create_contact(client):
    """Test the creation of a new contact with valid data."""
    response = client.post('/api/contacts', json={
        'firstName': 'Test',
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    assert response.status_code == 201
    assert response.json['firstName'] == 'Test'
    assert len(response.json['emails']) == 1


def test_get_contacts(client):
    """Test retrieving the list of all contacts."""
    client.post('/api/contacts', json={
        'firstName': 'Test',
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    response = client.get('/api/contacts')
    assert response.status_code == 200
    assert len(response.json) == 1


def test_get_contact(client):
    """Test retrieving a specific contact by its ID."""
    create_response = client.post('/api/contacts', json={
        'firstName': 'Test',
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    contact_id = create_response.json['id']
    response = client.get(f'/api/contacts/{contact_id}')
    assert response.status_code == 200
    assert response.json['firstName'] == 'Test'


def test_update_contact(client):
    """Test updating an existing contact with new data."""
    create_response = client.post('/api/contacts', json={
        'firstName': 'Test',
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    contact_id = create_response.json['id']
    response = client.put(f'/api/contacts/{contact_id}', json={
        'firstName': 'Updated',
        'lastName': 'User',
        'emails': [{'email': 'updated@example.com'}]
    })
    assert response.status_code == 200
    assert response.json['firstName'] == 'Updated'


def test_delete_contact(client):
    """Test deleting an existing contact by its ID."""
    create_response = client.post('/api/contacts', json={
        'firstName': 'Test',
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    contact_id = create_response.json['id']
    response = client.delete(f'/api/contacts/{contact_id}')
    assert response.status_code == 204


def test_sql_injection(client):
    """Test if SQL injection attempts are properly handled."""
    response = client.post('/api/contacts', json={
        'firstName': "'; DROP TABLE contacts; --",
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    assert response.status_code in [400, 201]
    assert "error" in response.json or response.json['firstName'] != "'; DROP TABLE contacts; --"


def test_xss_injection(client):
    """Test if XSS injection attempts are properly handled."""
    response = client.post('/api/contacts', json={
        'firstName': "<script>alert('XSS')</script>",
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    assert response.status_code == 400 or response.status_code == 201
    assert "error" in response.json or "<script>" not in response.json['firstName']


def test_long_input(client):
    """Test handling of excessively long input data."""
    long_name = "A" * 10000
    response = client.post('/api/contacts', json={
        'firstName': long_name,
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    assert response.status_code == 400 or response.status_code == 201
    assert "error" in response.json or len(response.json['firstName']) < 255


def test_invalid_email(client):
    """Test validation for invalid email addresses."""
    response = client.post('/api/contacts', json={
        'firstName': 'Test',
        'lastName': 'User',
        'emails': [{'email': 'not-an-email'}]
    })
    assert response.status_code == 400
    assert "error" in response.json


def test_missing_fields(client):
    """Test creation of a contact with missing required fields."""
    response = client.post('/api/contacts', json={
        'firstName': '',
        'lastName': 'User'
    })
    assert response.status_code == 400
    assert "error" in response.json


def test_special_characters(client):
    """Test handling of names with special or non-standard characters."""
    response = client.post('/api/contacts', json={
        'firstName': "测试😊{}\"'",
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    assert response.status_code == 400 or response.status_code == 201
    assert "error" in response.json or "😊" in response.json['firstName']


def test_create_contact_missing_name(client):
    """Test error handling for missing required fields during contact creation."""
    response = client.post('/api/contacts', json={
        'firstName': '',
        'lastName': 'Smith',
        'emails': [{'email': 'test@example.com'}]
    })
    assert response.status_code == 400
    assert response.json['error'] == 'First name and last name are required'


def test_create_contact_invalid_email(client):
    """Test error handling for invalid email format during contact creation."""
    response = client.post('/api/contacts', json={
        'firstName': 'John',
        'lastName': 'Smith',
        'emails': [{'email': 'invalidemail'}]
    })
    assert response.status_code == 400
    assert response.json['error'] == 'Invalid email format: invalidemail'


def test_create_contact_email_too_long(client):
    """Test error handling for emails exceeding the maximum allowed length."""
    long_email = 'a' * 121 + '@example.com'
    response = client.post('/api/contacts', json={
        'firstName': 'John',
        'lastName': 'Smith',
        'emails': [{'email': long_email}]
    })
    assert response.status_code == 400
    assert response.json['error'] == f"Email is too long: {long_email}"


def test_delete_nonexistent_contact(client):
    """Test deletion attempt of a non-existent contact."""
    response = client.delete('/api/contacts/9999')  # assuming ID 9999 doesn't exist
    assert response.status_code == 404
    assert response.json['error'] == 'Contact not found'


def test_update_contact_without_emails(client):
    """Test updating a contact with an empty list of emails."""
    # Create test contact
    response = client.post('/api/contacts', json={
        'firstName': 'Test',
        'lastName': 'User',
        'emails': [{'email': 'test@example.com'}]
    })
    assert response.status_code == 201
    contact = response.json

    # Update the contact without emails
    response = client.put(f"/api/contacts/{contact['id']}", json={
        'firstName': 'Updated',
        'lastName': 'User',
        'emails': []
    })
    assert response.status_code == 200
    updated_contact = response.json
    assert updated_contact['firstName'] == 'Updated'
    assert updated_contact['lastName'] == 'User'
    assert updated_contact['emails'] == []


def test_cors_headers(client):
    """Test if CORS headers are properly configured and returned."""
    response = client.get('/api/contacts')
    assert response.headers['Access-Control-Allow-Origin'] == '*'
    assert response.headers['Access-Control-Allow-Methods'] == 'GET,PUT,POST,DELETE'
    assert response.headers['Access-Control-Allow-Headers'] == 'Content-Type'

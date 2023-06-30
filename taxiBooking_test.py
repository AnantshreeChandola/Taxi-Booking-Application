import pytest
from flask import Flask
from taxiBooking import app as flask_app
from taxiBooking import db, Appointment
from datetime import datetime

@pytest.fixture
def app():
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_get_appointments_empty(client):
    response = client.get('/appointments/ServiceOperator0')
    assert response.status_code == 200
    assert response.get_json() == []

def test_book_appointment(client):
    response = client.post('/appointment/book', json={'operator': 'ServiceOperator0', 'start_time': 10, 'end_time': 11})
    assert response.status_code == 200
    appointment = response.get_json()
    assert appointment['operator'] == 'ServiceOperator0'
    assert appointment['start_time'] == 10
    assert appointment['end_time'] == 11

def test_get_appointments_after_booking(client):
    response = client.get('/appointments/ServiceOperator0')
    assert response.status_code == 200
    appointments = response.get_json()
    assert len(appointments) == 1
    assert appointments[0]['operator'] == 'ServiceOperator0'
    assert appointments[0]['start_time'] == 10
    assert appointments[0]['end_time'] == 11

def test_book_conflicting_appointment(client):
    response = client.post('/appointment/book', json={'operator': 'ServiceOperator0', 'start_time': 10, 'end_time': 11})
    assert response.status_code == 400
    assert response.get_json() == {'error': 'Appointment conflicts with an existing appointment'}

def test_cancel_appointment(client):
    response = client.get('/appointments/ServiceOperator0')
    appointment_id = response.get_json()[0]['id']
    
    response = client.delete(f'/appointment/cancel/{appointment_id}')
    assert response.status_code == 200
    cancelled_appointment = response.get_json()
    assert cancelled_appointment['deleted_at'] is not None

def test_get_appointments_after_cancelling(client):
    response = client.get('/appointments/ServiceOperator0')
    assert response.status_code == 200
    assert response.get_json() == []

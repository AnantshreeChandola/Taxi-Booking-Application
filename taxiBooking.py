from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scheduler.db'
db = SQLAlchemy(app)
ma = Marshmallow(app)

#timebased schema
#deleted_at is None for existing/valid appointments
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    operator = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.Integer, nullable=False)
    end_time = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

class AppointmentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Appointment

appointment_schema = AppointmentSchema()
appointments_schema = AppointmentSchema(many=True)

@app.route('/appointments/<operator>', methods=['GET'])
def get_appointments(operator):
    try:
        appointments = Appointment.query.filter_by(operator=operator, deleted_at=None).all()
        if not appointments:
            return jsonify([]), 200
        return appointments_schema.jsonify(appointments), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while getting all booked appointment slots for this operator: '+ operator + str(e)}), 500

@app.route('/free_slots/<operator>', methods=['GET'])
def get_free_slots(operator):
    try:
        appointments = Appointment.query.filter_by(operator=operator, deleted_at=None).all()
        times = sorted([(a.start_time, a.end_time) for a in appointments])
        free_slots = []
        start_time = 0
        for time_range in times:
            if start_time < time_range[0]:
                free_slots.append({'start_time': start_time, 'end_time': time_range[0]})
            start_time = time_range[1]
        if start_time < 24:
            free_slots.append({'start_time': start_time, 'end_time': 24})
        return jsonify(free_slots), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while getting the free slots for this operator: '+ operator + str(e)}), 500

@app.route('/appointment/book', methods=['POST'])
def add_appointment():
    operator = request.json['operator']
    start_time = request.json['start_time']
    end_time = request.json['end_time']

    # Validate that appointment is only 1 hour long
    if end_time - start_time != 1:
        return jsonify({'error': 'Appointments must be exactly 1 hour long.'}), 400

    try:
        appointments = Appointment.query.filter_by(operator=operator, deleted_at=None).all()
        for appointment in appointments:
            if appointment.start_time < end_time and start_time < appointment.end_time:
                return jsonify({'error': 'Appointment conflicts with an existing appointment'}), 400
        new_appointment = Appointment(operator=operator, start_time=start_time, end_time=end_time)
        db.session.add(new_appointment)
        db.session.commit()
        return appointment_schema.jsonify(new_appointment), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while adding the appointment' + str(e)}), 500

@app.route('/appointment/reschedule/<id>', methods=['PUT'])
def reschedule_appointment(id):
    try:
        appointment = Appointment.query.get(id)
        if appointment is None:
            return jsonify({'error': 'Appointment not found'}), 404
        start_time = request.json['start_time']
        end_time = request.json['end_time']

        # Validate that appointment is only 1 hour long
        if end_time - start_time != 1:
            return jsonify({'error': 'Appointments must be exactly 1 hour long.'}), 400

        appointments = Appointment.query.filter_by(operator=appointment.operator, deleted_at=None).all()
        for app in appointments:
            if app.id != appointment.id and app.start_time < end_time and start_time < app.end_time:
                return jsonify({'error': 'Appointment conflicts with an existing appointment'}), 400

        appointment.start_time = start_time
        appointment.end_time = end_time
        
        db.session.commit()
        return appointment_schema.jsonify(appointment), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while rescheduling the appointment: ' + id + str(e)}), 500

@app.route('/appointment/cancel/<id>', methods=['DELETE'])
def cancel_appointment(id):
    try:
        appointment = Appointment.query.get(id)
        if appointment is None:
            return jsonify({'error': 'Appointment not found'}), 404
        appointment.deleted_at = datetime.utcnow()
        db.session.commit()
        return appointment_schema.jsonify(appointment), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while cancelling the appointment: ' + id + str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

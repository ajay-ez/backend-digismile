from flask import Blueprint, request, jsonify
from backend import db, bcrypt, mail
from backend.models import Users, Appointment, doctor, DoctorAvailabilty, MedicalRecord
from backend.auth import encode_token
from datetime import datetime, timedelta
import uuid
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import jwt
from backend.utils import generate_random_password
from flask_mail import Mail, Message
from backend.calender import add_appointment, get_google_credentials, cancel_event
import json

main = Blueprint('main', __name__)


@jwt.unauthorized_loader
def custom_unauthorized_response(callback):
    return jsonify({'message': 'Invalid or missing token', 'status_code': 401}), 401


@main.route('/')
def hello():
    return 'backend has initialized'


@main.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password are required', 'status_code': 404}), 404
    
    user = Users.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'email not registered', 'status_code': 404}), 404

    if bcrypt.check_password_hash(user.password_hash, password):
        token = encode_token(user)
        return jsonify({'message': 'Login Successful', 'token': token, 'user_id': user.user_id, 'status_code': 200}), 200
    return jsonify({'message': 'Invalid Credentials', 'status_code': 400}), 400


@main.route('/register', methods=['POST'])
def register():
    data = request.json
    # Extract user details from the request
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    name = f"{first_name} {last_name}".strip()
    email = data.get('email')
    password = data.get('password')
    date_of_birth = data.get('date_of_birth')
    address = data.get('address')
    phone_number = data.get('phone_number')

    # Validate the input
    if not all([name, email, password]):
        return jsonify({'message': 'Name, email and password are required', 'status_code': 400}), 400

    # Check if the email already exists
    if Users.query.filter_by(email=email).first():
        return jsonify({'message': 'Email is already registered', 'status_code': 400}), 400
    
    # Hash the password
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    # Create new user Instance
    new_user = Users(
        name = name,
        email = email,
        password_hash = password_hash,
        date_of_birth = date_of_birth,
        address = address,
        phone_number = phone_number,
        role='patient'
    )

    # Add the new user to the database
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully!', 'status_code': 201}), 201


@main.route('/book_appointment_existing_user', methods=['POST'])
@jwt_required()
def book_appointment_existing_user(): #If user has logged in
    try:
        user_token = json.loads(get_jwt_identity())
        print('user_token :', user_token)
        print("Type of user_token:", type(user_token))
        print("Value of user_token:", user_token)
        # if isinstance(user_token, str):
        #     user_token = json.loads(user_token)
        user_id = user_token['user_id']
        print("user_id ------->>>", user_id)
        doctor_id = "033273c5-25e5-4b26-b125-a0a4b2e594d7"
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No input data provided', 'status_code': 400}), 400

        # appointment_date = datetime.strptime(data.get('appointment_date'), '%Y-%m-%d').date()
        # start_time = datetime.strptime(data.get('start_time'), '%H:%M:%S').time()
        # end_time = datetime.strptime(data.get('end_time'), '%H:%M:%S').time()
        # description = data.get('description', '')
        try:
            appointment_date = datetime.strptime(data.get('appointment_date'), '%Y-%m-%d').date()
            start_time = datetime.strptime(data.get('start_time'), '%H:%M:%S').time()
            end_time = datetime.strptime(data.get('end_time'), '%H:%M:%S').time()
            description = data.get('description', '')
            location = data.get('location', '')
            appointment_creation = datetime.now()
            appointment_creation_formatted = appointment_creation.strftime('%y-%m-%d %H:%M:%S')

        except (TypeError, ValueError) as e:
            return jsonify({'message': 'Invalid date or time format. Please provide valid values.', 'status_code': 400}), 400
        user = Users.query.filter_by(user_id=user_id).first()
        get_google_credentials()
        event_id = add_appointment(user.email, appointment_date, start_time, end_time, description)

        new_appointment = Appointment(
            user_id=user_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            description=description,
            status='scheduled',
            event_id = event_id,
            location = location,
            appointment_creation = appointment_creation_formatted
        )


        db.session.add(new_appointment)
        db.session.commit()
        user = Users.query.filter_by(user_id=user_id).first()
        email = user.email

        print(f'start_time : {start_time}, {appointment_date}')
        

        return jsonify({'message': 'Appointment booked successfully!', 'appointment_id':str(new_appointment.appointment_id), 'status_code': 201}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'An error occurred while booking the appointment', 'status_code': 500}), 500


@main.route('/get_appointments', methods=['POST'])
def get_appointments():
    try:
        data = request.get_json()
        city = data.get('city')
        appointment_date = data.get('appointment_date')
        if not appointment_date:
            return jsonify({'error': 'appointment_date is required', 'status_code': 400}), 400
        
        try:
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD', 'status_code': 400}), 400
        # Office hours based on the city
        office_hours = {
            'dc': {
                'Monday': ('10:00', '17:00'),
                'Wednesday': ('10:00', '17:00'),
                'Friday': ('10:00', '17:00')
            },
            'burke': {
                'Tuesday': ('09:00', '16:00'),
                'Thursday': ('09:00', '16:00'),
                'Saturday': ('09:00', '16:00')
            }
        }

        weekday = appointment_date.strftime('%A')
        print(weekday)

        if city not in office_hours or weekday not in office_hours[city]:
            return jsonify({'error': 'Office is closed on this day', 'status_code': 200}), 200

        open_time_str, close_time_str = office_hours[city][weekday]
        open_time = datetime.strptime(open_time_str, '%H:%M').time()
        close_time = datetime.strptime(close_time_str, '%H:%M').time()

        current_time = datetime.combine(appointment_date, open_time)
        close_time = datetime.combine(appointment_date, close_time)
        available_slots = []
        while current_time + timedelta(hours=1) <= close_time:
            available_slots.append({
                'start_time': current_time.time().strftime('%H:%M'),
                'end_time': (current_time + timedelta(hours=1)).time().strftime('%H:%M')
            })
            current_time += timedelta(hours=1)

        

        # current_appointments = Appointment.query.all()
        booked_appointments = Appointment.query.filter_by(appointment_date=appointment_date).all()
        print(booked_appointments)
        booked_slots = []
        for appointment in booked_appointments:
            booked_slots.append({
                'start_time': appointment.start_time.strftime('%H:%M'),
                'end_time': appointment.end_time.strftime('%H:%M')
            })
        print(f'booked_slots{booked_slots}')
        result_slots = []
        print(f'availablr_slots {available_slots}')
        for slot in available_slots:
            if any(slot['start_time'] == booked['start_time'] and slot['end_time'] == booked['end_time'] for booked in booked_slots):
                slot['status'] = 'booked'
            else:
                slot['status'] = 'available'
            result_slots.append(slot)
        return jsonify({'slotss': result_slots, 'status_code': 200}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'status_code': 500}), 500    


@main.route('/add_medical_record', methods=['POST'])
@jwt_required()
def add_medical_record():
    data = request.get_json()
    user_token = get_jwt_identity()
    user_id_staff = user_token['user_id']
    staff_user = Users.query.filter_by(user_id=user_id_staff).first()
    print(user_id_staff)    
    print(staff_user.role)
    # Validate JWT user identity and role
    if staff_user.role != 'staff':
        return jsonify({'message': 'Only staff members are authorized to add records', 'status_code': 403}), 403

    # Extract data from request
    email = data.get('email')
    prescription = data.get('prescription')
    problem = data.get('problem')
    document = data.get('document')  # Optional, can be None if not provided
    date = data.get('date')

    # Validate required fields
    missing_fields = [field for field in ['email', 'prescription', 'problem', 'date'] if not data.get(field)]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}', 'status_code': 400}), 400

    # Validate if user exists
    print(email)
    user = Users.query.filter_by(email=email).first()
    print(user)
    if not user:
        return jsonify({'error': 'User not found', 'status_code': 404}), 404

    # Create and save the new medical record
    new_record = MedicalRecord(
        email=email,
        prescription=prescription,
        problem=problem,
        document=document,
        date=date
    )
    try:
        db.session.add(new_record)
        db.session.commit()
        return jsonify({'message': 'Medical record added successfully!', 'status_code': 201}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to add medical record', 'details': str(e), 'status_code': 500}), 500


@main.route('/get_medical_records/<uuid:user_id>', methods=['GET'])
def get_medical_records(user_id):
    # fetch the user by user_id
    user = Users.query.filter_by(user_id=user_id).first()
    print('name: ', user.email)
    # If user does't exist return error
    if not user:
        return jsonify({'message': 'User not Found'}), 404
    
    # Query the MedicalRecord table for the user's records
    medical_records = MedicalRecord.query.filter_by(email=user.email).all()

    # If no records found, return an error
    if not medical_records:
        return jsonify({'message': 'No medical records found for the user'}), 404
    
    records = []
    for record in medical_records:
        records.append({
            'email': record.email,
            'prescription': record.prescription,
            'problem': record.problem,
            'document': record.document,
            'date': record.date
        })

    return jsonify({
        'user_id': user_id,
        'medical_records': records
    }), 200


@main.route('/get_user_appointments/<uuid:user_id>', methods=['GET'])
def get_user_appointments(user_id):
    user = Users.query.filter_by(user_id=user_id).first()
    print("email: ", user.email)
    if not user:
        return jsonify({'message': 'User not Found'}), 404
    
    all_appointments = Appointment.query.filter_by(user_id=user_id).all()
    print("all_appointments:", all_appointments)
    upcoming_app = []

    prev_app = []
    for a in all_appointments:
        today = datetime.today().date()
        if a.appointment_date <= today:
            prev_app.append({
            'date': str(a.appointment_date),
            'start_time': str(a.start_time),
            'end_time': str(a.end_time),
            'description': a.description
            })
            print(f'appointment_id {a.appointment_id} is previous appointment')

        else:
            if a.status == 'cancelled':
                print(f"appointment_id {a.appointment_id} is cancelled")
                pass
            else:
                upcoming_app.append({
                'date': str(a.appointment_date),
                'start_time': str(a.start_time),
                'end_time': str(a.end_time),
                'description': a.description,
                'appointment_id': a.appointment_id
                })
                print(f'appointment_id {a.appointment_id} is upcoming appointment')

    return jsonify({
        'user_id': user_id,
        'previous_appointments': prev_app,
        'upcoming_appointments': upcoming_app,
        'status_code': 200
    }), 200


@main.route('/get_user_details', methods=['GET'])
@jwt_required()
def get_user_details():
    try:
        print("calling get_user_details API")
        user_token = get_jwt_identity()
        if not user_token:
            print("no user token provided!")
            return jsonify({'message': 'no_token', 'status_code': 404}), 404

        user_id = user_token['user_id']
        print("user_token :", user_token)
        print("user_id :", user_id)
        user = Users.query.filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'message': 'User not found', 'status_code': 404}), 404

        email = user.email
        name = user.name
        print(name)
        try:
            first_name, last_name = name.split(' ', 1)
        except:
            first_name = name
            last_name  = " "
        dob = user.date_of_birth
        formatted_date = dob.strftime("%d-%m-%Y")
        address = user.address
        problem = user.problem
        phone_number = user.phone_number
        user_type = user.role

        return jsonify({'name': name,
                        'first_name' : first_name,
                        'last_name': last_name,
                        'email': email,
                        'dob': formatted_date,
                        'address': address,
                        'problem': problem,
                        'phone_number': phone_number,
                        'user_type': user_type,
                        'status_code': 200
                        }), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'An error occurred while fetching user details', 'status_code': 500}), 500


@main.route('/new_user_appointment', methods=['POST'])
def new_user_appointment():

    data = request.json

    first_name = data.get('first_name').strip()
    last_name = data.get('last_name').strip()
    email = data.get('email')
    date_of_birth = data.get('date_of_birth')
    phone_number = data.get('phone_number')
    problem = data.get('problem')

    if not all([first_name, last_name, email, date_of_birth, phone_number, problem]):
        return jsonify({'message': 'All fields are required', 'status_code': 400}), 400
    
    existing_user = Users.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'message': 'Email is already registered', 'status_code': 400}), 400
    
    generated_password = generate_random_password()

    password_hash = bcrypt.generate_password_hash(generated_password).decode('utf-8')
    name = first_name + ' ' + last_name
    doctor_id = "033273c5-25e5-4b26-b125-a0a4b2e594d7"
    appointment_date = data.get('appointment_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    description = data.get('description')
    try:
        new_user = Users(
            name = name,
            email = email,
            password_hash = password_hash,
            date_of_birth = date_of_birth,
            address = 'not_added',
            phone_number = phone_number,
            role='patient'
        )

        db.session.add(new_user)
        db.session.commit()
        user = Users.query.filter_by(email=email).first()


        new_appointment = Appointment(
            user_id=user.user_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            description=description,
            status='scheduled'
        )


        db.session.add(new_appointment)
        db.session.commit()
        add_appointment(email, appointment_date, start_time, end_time, description)


        msg = Message('Your Account Details for Digismile',
                    recipients=[email])
        msg.body = f"Dear {first_name}, Your account has been created successfully. Please use the following credentials to log in:\n\nEmail: {email}\nPassword: {generated_password}\n\nThank you!"
        mail.send(msg)
        return jsonify({'message': 'Appointment booked successfully!', 'appointment_id':str(new_appointment.appointment_id), 'status_code': 201}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'failed to book appointment.', 'error': str(e), 'status_code': 500}), 500
    

@main.route('/change_password', methods=['POST'])
@jwt_required()
def change_password():
    try:
        data = request.get_json()

        user_token = get_jwt_identity()
        print(f'user token : {user_token}')
        user_id = user_token["user_id"]
        print(data)
        old_pass = data.get('old_password')
        new_pass = data.get('new_password')

        if not old_pass or not new_pass:
            return jsonify({'message': 'Old password and new password are required!', 'status_code': 400}), 400
        
        user = Users.query.filter_by(user_id=user_id).first()

        if not user:
            return jsonify({'message':'user not found','status_code': 404}), 404
        
        if not bcrypt.check_password_hash(user.password_hash, old_pass):
            return jsonify({'message': 'Old password is incorrect!','status_code': 401}), 401
        
        new_pass_hash = bcrypt.generate_password_hash(new_pass).decode('utf-8')
        user.password_hash = new_pass_hash
        db.session.commit()

        return jsonify({'message':'Password updated successfully', 'status_code': 200}), 200
    
    except Exception as e:
        print(f"error {e}")
        return jsonify({'message': 'An error occured', 'status_code': 500}), 500


@main.route('/cancel_appointment', methods=['POST'])
def cancel_appointment():
    try:
        data = request.get_json()
        appointment_id = data.get('appointment_id')
        if not appointment_id:
            return jsonify({'error': 'appointment_id is required!!', 'status_code': 400}), 400
        
        appointment = Appointment.query.filter_by(appointment_id=appointment_id).first()
        if not appointment:
            return jsonify({'error': 'appointment not found', 'status_code': 400}), 400
        
        event_id = appointment.event_id
        if not event_id:
            return jsonify({'error': 'No event found for given appointment_id', 'status_code': 400}), 400
        
        appointment.status = 'cancelled'
        db.session.commit()

        credentials = get_google_credentials()
        print('1')
        cancel_event(event_id, credentials)
        print('2')
        return jsonify({'message': 'Appointment cancelled succesfully', 'status_code': 200}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'status_code': 500}), 500


@main.route('/forget_password', methods=['POST'])
def forget_password():
    data = request.json
    email = data.get('email').strip()
    user = Users.query.filter_by(email=email).first()

    generated_password = generate_random_password()
    password_hash_new = bcrypt.generate_password_hash(generated_password).decode('utf-8')

    user.password_hash = password_hash_new
    db.session.commit()

    msg = Message('Your Account Details for Digismile',
                    recipients=[email])
    msg.body = f"Dear User, Your account has been resetted. Please use the following credentials to log in:\n\nEmail: {email}\nPassword: {generated_password}\n\nThank you!"
    mail.send(msg)
    return jsonify({'message': 'forget success!!', 'status_code': 201}), 201


@main.route('/reschedule_appointment', methods=['POST'])
def reschedule_appointment():
    data = request.json
    email = data.get('email').strip()
    appointment_id = data.get('appointment_id')
    

@main.route('/get_appointments', methods=['GET'])
def get_appointments():
    data = request.json
    appointment_date = data.get('appointment_date', '') #yyyy-mm-dd
    if appointment_date:
        try:
            formatted_date = datetime.strptime(appointment_date, '%Y-%m-%d')
            print(formatted_date)
        except ValueError:
            print("Invalid date format. Expected YYY-MM-DD")
    else:
        print("No appointment date provided")
        return jsonify({'message': 'No appointment date provided', 'status_code': 400}), 400
    
    all_appointments = Appointment.query.filter_by(appointment_date=formatted_date).all()
    appointments = []
    for a in all_appointments:
        if a.appointment_date == formatted_date:
            appointments.append({
            'date': str(a.appointment_date),
            'start_time': str(a.start_time),
            'end_time': str(a.end_time),
            'description': a.description
            })
            print(f'appointment_id {a.appointment_id} is for day ')


    
    

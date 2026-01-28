from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response,make_response
from database import db
from functools import wraps
from datetime import datetime, timedelta
from dronekit import connect, VehicleMode, Command
from pymavlink import mavutil
import bcrypt
import csv
from io import StringIO
import os
import threading 
import uuid
import qrcode
from io import BytesIO
import cv2
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Add this at the top with other global variables
active_registrations = {}
mission_status = {}

parking_records = {}

# Add these performance settings at the top
@app.route('/')
def index():
    return render_template('homepage.html')

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            print('Session at protected route:', dict(session))
            if 'user_id' not in session:
                print('No user_id in session')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                print(f"Role mismatch: session role={session.get('role')} required={role}")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')

            print(f"[DEBUG] Login attempt: email={email}, role={role}")

            if not email or not password or not role:
                print("[DEBUG] Missing email, password, or role")
                return render_template('login.html', error='Email, password, and role are required')

            if role == 'admin':
                user = db.admins.find_one({'email': email})
            else:
                user = db.operators.find_one({'email': email})

            print(f"[DEBUG] User found: {user}")

            if user:
                password_matches = bcrypt.checkpw(password.encode('utf-8'), user['password'])
                print(f"[DEBUG] Password matches: {password_matches}")
            else:
                password_matches = False

            if user and password_matches:
                session['user_id'] = str(user['_id'])
                session['role'] = user['role']
                session['name'] = user['name']
                print(f"[DEBUG] Login successful, session: {{'user_id': session['user_id'], 'role': session['role'], 'name': session['name']}}")
                # Update last login time
                if user['role'] == 'admin':
                    db.admins.update_one(
                        {'_id': user['_id']},
                        {'$set': {'last_login': datetime.now()}}
                    )
                else:
                    db.operators.update_one(
                        {'_id': user['_id']},
                        {'$set': {'last_login': datetime.now()}}
                    )
                if user['role'] == 'admin':
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('operator'))
            else:
                print("[DEBUG] Invalid email, password, or role")
                return render_template('login.html', error='Invalid email, password, or role')
        except Exception as e:
            print(f"[DEBUG] Login error: {str(e)}")
            return render_template('login.html', error=f'Login error: {str(e)}')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            role = request.form.get('role')

            print(f"[DEBUG] Signup attempt: name={name}, email={email}, role={role}")

            if not all([name, email, password, confirm_password, role]):
                print("[DEBUG] Missing required fields")
                return render_template('signup.html', error='All fields are required')

            if password != confirm_password:
                print("[DEBUG] Passwords do not match")
                return render_template('signup.html', error='Passwords do not match')

            duplicate_operator = db.operators.find_one({'email': email})
            duplicate_admin = db.admins.find_one({'email': email})
            print(f"[DEBUG] Duplicate operator: {duplicate_operator}")
            print(f"[DEBUG] Duplicate admin: {duplicate_admin}")
            if duplicate_operator or duplicate_admin:
                print("[DEBUG] Email already registered")
                return render_template('signup.html', error='Email already registered')

            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            user_data = {
                'name': name,
                'email': email,
                'password': hashed_password,
                'role': role,
                'created_at': datetime.now(),
                'last_login': None
            }
            print(f"[DEBUG] Inserting user_data: {user_data}")

            if role == 'admin':
                result = db.admins.insert_one(user_data)
                print(f"[DEBUG] Inserted admin with id: {result.inserted_id}")
            else:
                result = db.operators.insert_one(user_data)
                print(f"[DEBUG] Inserted operator with id: {result.inserted_id}")

            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"[DEBUG] Signup error: {str(e)}")
            return render_template('signup.html', error=f'Error creating account: {str(e)}')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required(role='admin')
def admin():
    print('Accessing admin dashboard, session:', dict(session))
    return render_template('admin.html')

@app.route('/operator')
@login_required(role='operator')
def operator():
    return render_template('operator.html')

@app.route('/admin/parking-stats')
def parking_stats():
    try:
        # Get total slots
        total_slots = db.slots.count_documents({})
        
        # Get occupied slots (both occupied and reserved)
        occupied = db.slots.count_documents({
            'status': 'occupied'
        })
        
        # Get reserved slots
        reserved = db.slots.count_documents({
            'status': 'reserved'
        })
        
        # Calculate available slots
        available = total_slots - occupied-reserved
        
        # Get active parking records count
        active_records = db.parking_records.count_documents({
            'status': 'active'
        })
        
        return jsonify({
            'total_slots': total_slots,
            'occupied_slots': occupied,
            'reserved_slots': reserved,
            'available_slots': available,
            'active_records': active_records
        })
    except Exception as e:
        print(f"Error getting parking stats: {str(e)}")
        return jsonify({
            'total_slots': 0,
            'occupied_slots': 0,
            'reserved_slots': 0,
            'available_slots': 0,
            'active_records': 0
        })

@app.route('/admin/generate-report', methods=['POST'])
def generate_report():
    try:
        start_date = request.json.get('start_date')
        end_date = request.json.get('end_date')
        
        query = {}
        if start_date and end_date:
            query['entry_time'] = {
                '$gte': datetime.fromisoformat(start_date),
                '$lte': datetime.fromisoformat(end_date)
            }
        
        records = list(db.parking_records.find(query, {
            '_id': 0,
            'license_plate': 1,
            'vehicle_type': 1,
            'entry_time': 1,
            'exit_time': 1,
            'status': 1
        }))
        
        for record in records:
            record['entry_time'] = record['entry_time'].isoformat() if record['entry_time'] else None
            record['exit_time'] = record['exit_time'].isoformat() if record['exit_time'] else None
            record['duration'] = calculate_duration(record['entry_time'], record['exit_time'])
        
        return jsonify(records)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/sort-report', methods=['POST'])
def sort_report():
    try:
        sort_by = request.json.get('sort_by', 'entry_time')
        order = request.json.get('order', 'desc')
        
        records = list(db.parking_records.find({}, {
            '_id': 0,
            'license_plate': 1,
            'vehicle_type': 1,
            'entry_time': 1,
            'exit_time': 1,
            'status': 1
        }).sort(sort_by, -1 if order == 'desc' else 1))
        
        for record in records:
            record['entry_time'] = record['entry_time'].isoformat() if record['entry_time'] else None
            record['exit_time'] = record['exit_time'].isoformat() if record['exit_time'] else None
            record['duration'] = calculate_duration(record['entry_time'], record['exit_time'])
        
        return jsonify(records)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/export-report')
def export_report():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    try:
        records = list(db.parking_records.find({}, {
            'plate_number': 1,
            'name': 1,
            'slot': 1,
            'lot':1,
            'entry_time': 1,
            'exit_time': 1,
            '_id': 0
        }))
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['License Plate', 'Name', 'Parking Lot', 'Slot', 'Entry Time', 'Exit Time', 'Status'])
        
        for record in records:
            writer.writerow([
                record['plate_number'],
                record['name'],
                record['lot'],
                record['slot'],
                record['entry_time'].strftime('%Y-%m-%d %H:%M:%S'),
                record['exit_time'].strftime('%Y-%m-%d %H:%M:%S') if record.get('exit_time') else 'Currently Parked',
                'Exited' if record.get('exit_time') else 'Parked'
            ])
        
        output.seek(0)
        return Response(
            output,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=parking_report.csv'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/parking-slots')
@login_required(role='admin')
def get_parking_slots():
    return render_template('parking_slots.html')


@app.route('/book_slot_form')
def book_slot_form():
    return render_template('book_slot.html')

@app.route('/book_slot', methods=['POST'])
def book_slot():
    name = request.form['name']
    phone = request.form['phone']
    plate = request.form['plate'].upper().strip()

    existing = db.bookings.find_one({
        "plate_number": plate,
        "status": "booked"
    })

    if existing:
        flash("This license plate already has an active booking.")
        return redirect(url_for('book_slot_form'))
    # Assign a slot
    slot_data = db.slots.find_one_and_update(
        {"status": "empty"},
        {"$set": {"status": "reserved", "current_vehicle": plate, "last_updated": datetime.now()}},
        sort=[("space_id", 1)]
    )

    if not slot_data:
        flash("No slots available.")
        return redirect(url_for('book_slot_form'))

    slot_no = slot_data['space_id']
    lot_id = slot_data.get('lot_id', 'N/A')

    booking = {
        "plate_number": plate,
        "slot_no": slot_no,
        "lot_id": lot_id,
        "status": "booked",
        "booking_time": datetime.now(),
        "name": name,
        "phone": phone
    }
    db.bookings.insert_one(booking)

    # Store booking data temporarily for download
    session['last_booking'] = {
        "name": name,
        "phone": phone,
        "plate": plate,
        "slot_no": slot_no,
        "lot_id": lot_id,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    return render_template("booking-success.html", plate=plate, slot_no=slot_no, lot_id=lot_id)

@app.route('/download_ticket')
def download_ticket():
    ticket = session.get('last_booking')
    if not ticket:
        return "No recent booking", 400

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial;
                padding: 40px;
            }}
            .ticket {{
                border: 2px dashed #333;
                padding: 30px;
                width: 400px;
                margin: auto;
                text-align: center;
            }}
            h2 {{
                color: #10b981;
            }}
        </style>
    </head>
    <body>
        <div class="ticket">
            <h2>Parking Ticket</h2>
            <p><b>Name:</b> {ticket['name']}</p>
            <p><b>Phone:</b> {ticket['phone']}</p>
            <p><b>Plate:</b> {ticket['plate']}</p>
            <p><b>Lot:</b> {ticket['lot_id']}</p>
            <p><b>Slot:</b> {ticket['slot_no']}</p>
            <p><b>Time:</b> {ticket['time']}</p>
        </div>
    </body>
    </html>
    """

    response = make_response(html)
    response.headers["Content-Disposition"] = f"attachment; filename=ticket_{ticket['plate']}.html"
    response.headers["Content-Type"] = "text/html"
    return response


@app.route('/admin/parking-slots-data')
@login_required(role='admin')
def get_parking_slots_data():
    try:
        slots = list(db.slots.find({}, {
            '_id': 0,
            'space_id': 1,
            'lot_id': 1,
            'status': 1,
            'current_vehicle': 1,
            'last_updated': 1
        }))
        
        for slot in slots:
            slot['last_updated'] = slot['last_updated'].isoformat() if slot['last_updated'] else None
            # Ensure lot_id is present
            if 'lot_id' not in slot:
                slot['lot_id'] = 'dummy_lot_6'
        
        return jsonify(slots)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/reports')
@login_required(role='admin')
def reports():
    return render_template('reports.html')

@app.route('/lot-upload')
@login_required(role='operator')
def upload_parking_lot():  # <-- this is the endpoint name
    return render_template('lot_upload.html')

@app.route('/admin/check-violations')
def check_violations():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    try:
        # Get all active parking records
        active_records = list(db.parking_records.find({
            'exit_time': None
        }))
        
        violations = []
        for record in active_records:
            # Check if the vehicle is in its assigned slot
            if record.get('assigned_slot') != record.get('current_slot'):
                violations.append({
                    'license_plate': record['license_plate'],
                    'assigned_slot': record['assigned_slot'],
                    'current_slot': record['current_slot'],
                    'detected_at': datetime.now()
                })
        
        return jsonify({'violations': violations})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/operator/add-parking-space', methods=['POST'])
def add_parking_space():
    data = request.get_json()
    space_id = data.get('id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    if space_id and latitude and longitude:
        space_data = {
            'space_id': space_id,
            'location': {
                'type': 'Point',
                'coordinates': [longitude, latitude]
            },
            'status': 'empty',
            'created_at': datetime.now(),
            'last_updated': datetime.now()
        }
        try:
            db.parking_slots.update_one(
                {'space_id': space_id},
                {'$set': space_data},
                upsert=True
            )
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Missing required data'})

from datetime import datetime

@app.route('/vehicle')
def vehicle_page():
    return render_template('vehicle.html')

from datetime import datetime
from flask import jsonify
from bson.json_util import dumps

@app.route('/vehicles-records/<lot_id>')
def get_vehicle_records(lot_id):
    try:
        records_cursor = db.parking_records.find(
            {
                'lot': lot_id,
                '$or': [
                    {'entry_time': None},
                    {'exit_time': None}
                ]
            },
            {
                '_id': 0,
                'lot': 1,
                'slot': 1,
                'status': 1,
                'plate_number': 1,
                'name': 1,
                'phone': 1,
                'entry_time': 1,
                'last_updated': 1
            }
        )

        records = []
        for r in records_cursor:
            r['entry_time'] = (
                r['entry_time'].isoformat()
                if r.get('entry_time') else None
            )
            r['last_updated'] = (
                r.get('last_updated', datetime.now()).isoformat()
            )
            records.append(r)

        return jsonify({'status': 'success', 'records': records})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/admin/vehicle-details/<lot_id>/<slot_id>')
def vehicle_details(slot_id):
    record = db.parking_records.find_one({'lot':lot_id,'slot': slot_id, 'exit_time': None})
    if not record:
        return jsonify({'status': 'error', 'message': 'Not found'}), 404

    record['entry_time'] = record['entry_time'].isoformat()
    record['last_updated'] = record.get('last_updated', datetime.now()).isoformat()

    return jsonify({'status': 'success', 'vehicle': record})



@app.route('/operator/parking-lot-coordinates')
def get_parking_lot_coordinates():
    try:
        parking_lot = db.parking_lots.find_one()
        if parking_lot:
            return jsonify({
                'center': parking_lot['location']['coordinates'],
                'boundaries': parking_lot['boundaries']['coordinates'],
                'name': parking_lot['name']
            })
        return jsonify({
            'center': [47.6062, -122.3321],
            'boundaries': [
                [47.6062, -122.3321],
                [47.6062, -122.3331],
                [47.6052, -122.3331],
                [47.6052, -122.3321]
            ],
            'name': 'Default Parking Lot'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/operator/parking-slots-data')
def operator_parking_slots_data():
    try:
        slots_cursor = db.slots.find()
        slots = []
        for slot in slots_cursor:
            vehicle_number = None
            if slot.get('current_vehicle_id'):
                vehicle = db.vehicles.find_one({'vehicle_id': slot['current_vehicle_id']})
                if vehicle:
                    vehicle_number = vehicle.get('license_plate')

            slots.append({
                'space_id': slot['space_id'],
                'lot_id': slot['lot_id'],
                'status': slot['status'],
                'last_updated': slot.get('last_updated', datetime.now()),
                'current_vehicle': vehicle_number
            })
        return jsonify(slots)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/operator/parking-spaces')
def get_parking_spaces():
    try:
        spaces = list(db.parking_slots.find({}, {
            '_id': 0,
            'slot_number': 1,
            'status': 1,
            'current_vehicle': 1,
            'last_updated': 1,
            'location': 1
        }))
        for space in spaces:
            if 'location' in space:
                space['coordinates'] = space['location']['coordinates']
                del space['location']
            else:
                space['coordinates'] = [0, 0]
            space.setdefault('slot_number', 'Unknown')
            space.setdefault('status', 'empty')
            space.setdefault('current_vehicle', None)
            space.setdefault('last_updated', datetime.now().isoformat())
        return jsonify(spaces)
    except Exception as e:
        return jsonify([])

@app.route('/operator/update-space-status', methods=['POST'])
def update_space_status():
    data = request.get_json()
    space_id = data.get('spaceId')
    new_status = data.get('status')
    if not space_id or not new_status:
        return jsonify({'error': 'Missing required data'}), 400
    try:
        db.parking_slots.update_one(
            {'space_id': space_id},
            {
                '$set': {
                    'status': new_status,
                    'last_updated': datetime.now()
                }
            }
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


vehicle = None
connection_string = 'tcp:127.0.0.1:5762'
def connect_rover():
    global vehicle
    try:
        print(f"Connecting to vehicle on: {connection_string}")
        vehicle = connect(connection_string, wait_ready=True, vehicle_class=None)
        print("Vehicle connected!")
        return True
    except Exception as e:
        print(f"Error connecting to vehicle: {e}")
        vehicle = None
        return False
@app.route('/operator/connect_rover_api', methods=['POST'])
def connect_rover_api():
    global vehicle
    if vehicle and vehicle.is_armable:
        return jsonify({'status': 'success', 'message': 'Already connected and vehicle is armable.'})
    if connect_rover():
        return jsonify({'status': 'success', 'message': 'Rover connected successfully.'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to connect Rover.'})
    return jsonify({'status': 'info', 'message': 'DroneKit connection logic is placeholder.'})

@app.route('/operator/rtl', methods=['POST'])
def return_to_launch():
    global vehicle
    if not vehicle:
        return jsonify({'status': 'error', 'message': 'Rover not connected.'}), 400
    try:
        print("Setting RTL mode")
        vehicle.mode = VehicleMode("RTL")
        print("Drone returning to launch.")
        return jsonify({'status': 'success', 'message': 'RTL command sent.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error setting RTL: {str(e)}'}), 500
    return jsonify({'status': 'info', 'message': 'RTL logic is placeholder.'})


@app.route('/admin/get-lots', methods=['GET'])
@login_required(role='admin')
def get_lots():
    lots = db.parking_lots.find({}, {"_id": 0, "lot_id": 1})  # Only return lot_id
    lot_ids = [lot["lot_id"] for lot in lots]
    return jsonify({'status': 'success', 'lots': lot_ids})

@app.route('/vehicle/get-lots', methods=['GET'])
def get_all_lots():
    lots = db.parking_lots.find({}, {"_id": 0, "lot_id": 1})  # Only return lot_id
    lot_ids = [lot["lot_id"] for lot in lots]
    return jsonify({'status': 'success', 'lots': lot_ids})

@app.route('/operator/arm-rover', methods=['POST'])
def arm_drone():
    global vehicle
    if not vehicle:
        return jsonify({'status': 'error', 'message': 'Rover not connected.'}), 400
    if vehicle.armed:
        return jsonify({'status': 'success', 'message': 'Rover is already armed.'})
    try:
        print("Arming motors")
        vehicle.mode = VehicleMode("GUIDED")
        vehicle.armed = True
        while not vehicle.armed:
            print(" Waiting for arming...")
            time.sleep(1)
        print("Drone armed!")
        return jsonify({'status': 'success', 'message': 'Rover armed successfully.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error arming Rover: {str(e)}'}), 500
    return jsonify({'status': 'info', 'message': 'Arming logic is placeholder.'})

@app.route('/operator/telemetry')
def get_telemetry():
    try:
        rover_id = request.args.get('rover_id')
        if not rover_id:
            return jsonify({'status': 'error', 'message': 'Rover ID required'}), 400
        
        rover = db.rovers.find_one(
            {'rover_id': rover_id},
            {
                '_id': 0,
                'status': 1,
                'battery_level': 1,
                'location': 1,
                'last_updated': 1
            }
        )
        
        if not rover:
            return jsonify({'status': 'error', 'message': 'Rover not found'}), 404
        
        rover['last_updated'] = rover['last_updated'].isoformat() if rover['last_updated'] else None
        if 'location' in rover:
            rover['coordinates'] = rover['location']['coordinates']
            del rover['location']
        
        return jsonify({
            'status': 'success',
            'data': rover
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def mission_runner(lot_id):
    global vehicle
    try:
        lot_data = db.parking_lots.find_one({"lot_id": lot_id})
        waypoints = lot_data.get('waypoints', [])

        if not waypoints or len(waypoints) < 2:
            print(f"[{lot_id}] Not enough waypoints to start mission.")
            return

        # Sort and prepare commands
        cmds = vehicle.commands
        cmds.clear()
        time.sleep(1)

        sorted_wps = sorted(waypoints, key=lambda x: x.get('index', 0))

        for wp in sorted_wps:
            cmd = Command(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0, 1,
                float(wp.get('delay', 0)),
                float(wp.get('param2', 10)),
                float(wp.get('param3', 0)),
                float(wp.get('param4', 0)),
                float(wp['lat']),
                float(wp['lon']),
                float(wp['alt'])
            )
            cmds.add(cmd)

        # Add RTL at the end
        cmds.add(Command(
            0, 0, 0,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            0, 1, 0, 0, 0, 0, 0, 0, 0
        ))

        cmds.upload()
        print(f"[{lot_id}] Uploaded {len(sorted_wps)} waypoints + RTL.")

        # Set to GUIDED
        vehicle.mode = VehicleMode("GUIDED")
        time.sleep(2)
        while vehicle.mode.name != "GUIDED":
            print("Waiting for GUIDED mode...")
            time.sleep(1)

        # Arm the vehicle
        vehicle.armed = True
        while not vehicle.armed:
            print("Waiting for arming...")
            time.sleep(1)

        # Start mission in AUTO
        vehicle.mode = VehicleMode("AUTO")
        while vehicle.mode.name != "AUTO":
            print("Waiting for AUTO mode...")
            time.sleep(1)

        print(f"[{lot_id}] Started AUTO mission")

        # Wait for all commands including RTL to finish
        num_cmds = len(sorted_wps)  # includes RTL
        timeout = time.time() + 600
        while vehicle.commands.next < num_cmds and time.time() < timeout:
            print(f"[{lot_id}] Executing WP {vehicle.commands.next}/{num_cmds}")
            time.sleep(2)

        # RTL executed, wait briefly
        print(f"[{lot_id}] RTL reached. Disarming in 5 seconds...")
        time.sleep(5)

        # Disarm vehicle
        if vehicle.armed:
            vehicle.armed = False
            while vehicle.armed and time.time() < timeout:
                print(f"[{lot_id}] Waiting for disarm...")
                time.sleep(1)
            print(f"[{lot_id}] Vehicle disarmed.")

        # Wait and re-arm before next mission
        print(f"[{lot_id}] Re-arming in 5 seconds...")
        time.sleep(5)
        vehicle.mode = VehicleMode("GUIDED")
        time.sleep(2)
        while vehicle.mode.name != "GUIDED":
            print(f"[{lot_id}] Waiting for GUIDED mode (re-arm)...")
            time.sleep(1)

        vehicle.armed = True
        while not vehicle.armed:
            print(f"[{lot_id}] Waiting for re-arming...")
            time.sleep(1)

        print(f"[{lot_id}] Mission completed and re-armed for next lot.")

    except Exception as e:
        print(f"[{lot_id}] Mission runner error: {str(e)}")


@app.route('/operator/start-patrol', methods=['POST'])
def start_patrol():
    global vehicle
    lot_ids = request.json.get('lot_ids', [])

    if not lot_ids or not isinstance(lot_ids, list):
        return jsonify({'status': 'error', 'message': 'lot_ids must be a non-empty list.'}), 400

    if not vehicle:
        return jsonify({'status': 'error', 'message': 'Drone not connected.'}), 400

    def mission_sequence_runner(lot_ids):
        for lot_id in lot_ids:
            print(f"=== Starting mission for lot: {lot_id} ===")
            mission_runner(lot_id)
            print(f"=== Finished mission for lot: {lot_id} ===")
            time.sleep(5)  # Optional delay between missions

    try:
        threading.Thread(target=mission_sequence_runner, args=(lot_ids,), daemon=True).start()
        return jsonify({'status': 'success', 'message': f'Started mission sequence: {lot_ids}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/operator/mission-status', methods=['GET'])
def get_mission_status():
    lot_id = request.args.get('lot_id')
    if not lot_id:
        return jsonify({'status': 'error', 'message': 'Missing lot_id'}), 400
    status = mission_status.get(lot_id, 'unknown')
    return jsonify({'status': status})


@app.route('/operator/stop-patrol', methods=['POST'])
def stop_patrol():
    return jsonify({'status': 'success'})

@app.route('/operator/mission-details')
def get_mission_details():
    return jsonify({'status': 'success', 'details': {}})



@app.route('/admin/parking-records')
@login_required(role='admin')
def get_parking_records():
    try:
        print("Inside /admin/parking-records route")

        # Query with correct field names
        records = list(db.parking_records.find({}, {
            '_id': 0,
            'parking_id': 1,
            'plate_number': 1,
            'name': 1,
            'phone': 1,
            'lot': 1,  # ✅ Correct field name
            'slot': 1,
            'entry_time': 1,
            'exit_time': 1,
            'status': 1,
            'registration_id': 1
        }))
        # Format records
        for record in records:
            record.setdefault('plate_number', '-')
            record.setdefault('name', '-')
            record.setdefault('phone', '-')
            record.setdefault('lot', 'dummy_lot_6')
            record.setdefault('slot', '-')
            record.setdefault('status', 'active')

            if isinstance(record.get('entry_time'), datetime):
                record['entry_time'] = record['entry_time'].isoformat()
            else:
                record['entry_time'] = '-'

            if record.get('status') == 'exited' and isinstance(record.get('exit_time'), datetime):
                record['exit_time'] = record['exit_time'].isoformat()
            else:
                record['exit_time'] = '-'

        return jsonify(records)
    except Exception as e:
        print(f"Error getting parking records: {str(e)}")
        return jsonify([])



@app.route("/operator/upload-waypoints-data", methods=["POST"]) 
@login_required(role='operator') # Added login_required
def upload_waypoints_data():
    lot_no = request.form.get("lot_id")
    if not lot_no:
        return jsonify({"status": "error", "message": "Missing lot_id"})

    if "waypointsFile" not in request.files:
        return jsonify({"status": "error", "message": "No file part"})
    file = request.files["waypointsFile"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected"})
    try:
        content = file.read().decode("utf-8").strip().splitlines()
        if not content or not content[0].startswith("QGC WPL"):
            return jsonify({"status": "error", "message": "Invalid QGC Waypoint file format"})
        waypoints = []
        slots = []
        for line in content[1:]:
            parts = line.strip().split('\t')
            if len(parts) < 12:
                continue
            delay = float(parts[4])
            lat = float(parts[8])
            lon = float(parts[9])
            alt = float(parts[10])
            wp = {
                "index": int(parts[0]),
                "lat": lat,
                "lon": lon,
                "alt": alt,
                "delay": delay
            }
            waypoints.append(wp)
            if delay == 2.0:
                slots.append(wp)

        # Save to parking_lots collection
        db.parking_lots.update_one(
            {"lot_id": lot_no},
            {"$set": {
                "lot_id": lot_no,
                "waypoints": waypoints,
                "slots": slots,
                "waypoints_uploaded_at": datetime.now()
            }},
            upsert=True
        )

        # Save slot docs to slots collection
        for idx, slot in enumerate(slots, start=1):
            slot_doc = {
                "parking_id": idx,  # Or generate a unique value if needed
                "space_id": idx,
                "slot_number": f"B{idx}",  # Or another logic for slot naming
                "lot_id": lot_no,
                "location": {
                    "type": "Point",
                    "coordinates": [slot["lon"], slot["lat"]]
                },
                "status": "empty",
                "current_vehicle": None,
                "last_updated": datetime.now(),
                "is_dummy": False
            }
            db.slots.update_one(
                {"lot_id": lot_no, "space_id": idx},
                {"$set": slot_doc},
                upsert=True
            )

        return jsonify({
            "status": "success",
            "lot_id": lot_no,
            "waypoints_count": len(waypoints),
            "slots_count": len(slots)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/operator/get-lot-s', methods=['GET'])
@login_required(role='operator')
def get_lot_s():
    lots = db.parking_lots.find({}, {"_id": 0, "lot_id": 1})  # Only return lot_id
    lot_ids = [lot["lot_id"] for lot in lots]
    return jsonify({'status': 'success', 'lots': lot_ids})


@app.route('/operator/get-lots')
@login_required(role='operator')
def get_lots_data():
    try:
        lots_cursor = db.parking_lots.find()  # Assuming your collection is 'parking_lots'
        lots = []
        for lot in lots_cursor:
            lots.append({
                "name": lot.get("lot_id", "Unnamed Lot"),
                "lot_id": lot.get("lot_id"),
                "slots": lot.get("slots", [])
            })
        return jsonify({"status": "success", "lots": lots})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/operator/get-lot/<lot_id>")
def get_lot(lot_id):
    lot = db.parking_lots.find_one({"lot_id": lot_id}, {"_id": 0})
    if lot:
        return jsonify({"status": "success", "lot": lot})
    return jsonify({"status": "error", "message": "Lot not found"})

@app.route('/admin/slot-details/<slot_id>')
@login_required(role='admin')
def slot_details(slot_id):
    try:
        # Find the latest active or most recent parking record for this slot
        record = db.parking_records.find_one(
            {'slot': slot_id},
            sort=[('entry_time', -1)]
        )
        if not record:
            return jsonify({})
        # Calculate duration
        entry_time = record.get('entry_time')
        exit_time = record.get('exit_time')
        now = datetime.now()
        duration = None
        if entry_time:
            if record.get('status') == 'exited' and exit_time:
                delta = exit_time - entry_time
            else:
                delta = now - entry_time
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes = remainder // 60
            duration = f"{int(hours)}h {int(minutes)}m"
        # Compose response
        return jsonify({
            'image_url': record.get('image_url'),
            'plate_number': record.get('plate_number'),
            'slot': record.get('slot'),
            'entry_time': entry_time.isoformat() if entry_time else None,
            'duration': duration,
            'status': record.get('status'),
            'phone': record.get('phone'),
            'parking_id': record.get('parking_id'),
        })
    except Exception as e:
        print(f"Error in slot_details: {str(e)}")
        return jsonify({})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)  # Set debug=True for development
from pymongo.mongo_client import MongoClient
from pymongo import GEOSPHERE
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta
import uuid



# MongoDB Atlas connection string - using direct connection
MONGO_URI = 'mongodb+srv://henrypete0086:Henry%4012345@cluster0.18yj3ms.mongodb.net/test?retryWrites=true&w=majority'
DB_NAME = 'Testing'

class Database:
    def __init__(self):
        try:
            # Using ServerApi to set MongoDB version with minimal configuration
            self.client = MongoClient(
                MONGO_URI,
                server_api=ServerApi('1'),
            )
            
            self.db = self.client[DB_NAME]
            # Collections
            self.users = self.db.users
            self.parking_records = self.db.parking_records
            self.bookings = self.db.bookings
            self.slots = self.db.slots
            self.operators = self.db.operators
            self.admins = self.db.admins
            self.rover_data = self.db.rover_data
            self.parking_lots = self.db.parking_lots
            self.temp_registrations = self.db.temp_registrations
            
            # Create geospatial index for parking lots
            self.parking_lots.create_index([("location", GEOSPHERE)])
            self.bookings.create_index('name')
            # Create indexes
            self.slots.create_index([('location', '2dsphere')])
            self.parking_records.create_index('plate_number')
            self.parking_records.create_index('entry_time')
            self.operators.create_index('email', unique=True)
            self.admins.create_index('email', unique=True)
            self.temp_registrations.create_index([('registration_id', 1)], unique=True)
            self.temp_registrations.create_index([('timestamp', 1)], expireAfterSeconds=3600)  # Expire after 1 hour

            # Test the connection
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB Atlas")
            
            # Initialize database and create dummy spaces
            self.initialize_database()
            
        except Exception as e:
            print(f"Error connecting to MongoDB: {str(e)}")
            raise

    def initialize_database(self):
        """Initialize the database with required collections and indexes"""
        try:
            # Create collections if they don't exist
            collections = ['parking_lots', 'slots', 'parking_records', 'operators', 'admins', 'temp_registrations']
            for collection in collections:
                if collection not in self.db.list_collection_names():
                    self.db.create_collection(collection)
                    print(f"Created collection: {collection}")

            # Create indexes

            self.slots.create_index([("lot_id", 1), ("space_id", 1)], unique=True)
            self.slots.create_index([('location', '2dsphere')])
            self.parking_records.create_index([('plate_number', 1)])
            self.parking_records.create_index([('lot_id',1),('entry_time', 1)], unique=True)
            self.operators.create_index([('email', 1)], unique=True)
            self.admins.create_index([('email', 1)], unique=True)
            self.temp_registrations.create_index([('registration_id', 1)], unique=True)
            self.temp_registrations.create_index([('timestamp', 1)], expireAfterSeconds=3600)  # Expire after 1 hour

            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")

    def create_parking_lot(self, data):
        """Create a new parking lot"""
        lot = {
            'name': data['name'],
            'place_id': data['place_id'],
            'location': {
                'type': 'Point',
                'coordinates': [data['longitude'], data['latitude']]
            },
            'address': data['address'],
            'total_slots': data['total_slots'],
            'boundaries': {
                'type': 'Polygon',
                'coordinates': data['boundary_coordinates']  # List of [lon, lat] points
            },
            'created_at': datetime.now(),
            'status': 'active',
            'features': data.get('features', []),  # e.g., ['covered', 'ev_charging', 'security']
            'hourly_rate': data.get('hourly_rate', 0),
            'operating_hours': data.get('operating_hours', {
                'monday': {'open': '00:00', 'close': '23:59'},
                'tuesday': {'open': '00:00', 'close': '23:59'},
                'wednesday': {'open': '00:00', 'close': '23:59'},
                'thursday': {'open': '00:00', 'close': '23:59'},
                'friday': {'open': '00:00', 'close': '23:59'},
                'saturday': {'open': '00:00', 'close': '23:59'},
                'sunday': {'open': '00:00', 'close': '23:59'}
            })
        }
        return self.parking_lots.insert_one(lot)

    def create_parking_record(self, data):
        """Create a new parking record"""
        # Generate a unique parking_id using UUID
        parking_id = str(uuid.uuid4())
        
        record = {
            'parking_id': parking_id,
            'plate_number': data['plate_number'],
            'user_name': data['name'],
            'phone': data['phone'],
            'lot_id': data['lot_id'],
            'slot_number': data['slot'],
            'slot_coordinates': {
                'type': 'Point',
                'coordinates': [data['slot_longitude'], data['slot_latitude']]
            },
            'entry_time': datetime.now(),
            'exit_time': None,
            'status': 'active',
            'vehicle_type': data.get('vehicle_type', 'Car'),
            'payment_status': 'pending',
            'confidence_score': data.get('confidence', 0),
            'created_at': datetime.now(),
            'place_id': data.get('place_id'),
            'zone': data.get('zone', 'general')
        }
        return self.parking_records.insert_one(record)

    def create_slot(self, data):
        """Create a new parking slot with coordinates"""
        slot = {
            'slot_number': data['slot_number'],
            'lot_id': data['lot_id'],
            'location': {
                'type': 'Point',
                'coordinates': [data['longitude'], data['latitude']]
            },
            'status': data.get('status', 'available'),
            'current_vehicle': None,
            'last_updated': datetime.now(),
            'zone': data.get('zone', 'general'),
            'type': data.get('type', 'standard'),  # standard, handicap, ev, etc.
            'dimensions': data.get('dimensions', {
                'length': 0,
                'width': 0
            }),
            'sensors': data.get('sensors', {
                'presence': None,
                'last_reading': None
            })
        }
        return self.slots.insert_one(slot)

    def find_nearby_lots(self, longitude, latitude, max_distance=1000):
        """Find parking lots within specified distance (meters)"""
        return list(self.parking_lots.find({
            'location': {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [longitude, latitude]
                    },
                    '$maxDistance': max_distance
                }
            }
        }))

    def get_lot_occupancy(self, lot_id):
        """Get current occupancy status of a parking lot"""
        total_slots = self.slots.count_documents({'lot_id': lot_id})
        occupied = self.slots.count_documents({
            'lot_id': lot_id,
            'status': 'occupied'
        })
        reserved = self.slots.count_documents({
            'lot_id': lot_id,
            'status': 'reserved'
        })
        
        return {
            'total_slots': total_slots,
            'occupied': occupied,
            'reserved': reserved,
            'available': total_slots - occupied - reserved
        }

    def update_slot_coordinates(self, slot_number, lot_id, longitude, latitude):
        """Update parking slot coordinates"""
        return self.parking_slots.update_one(
            {'slot_number': slot_number, 'lot_id': lot_id},
            {'$set': {
                'location': {
                    'type': 'Point',
                    'coordinates': [longitude, latitude]
                },
                'last_updated': datetime.now()
            }}
        )

    def update_parking_record(self, parking_id, update_data):
        """Update an existing parking record"""
        return self.parking_records.update_one(
            {'_id': parking_id},
            {'$set': update_data}
        )

    def get_active_parkings(self):
        """Get all active parking records"""
        return list(self.parking_records.find({'status': 'active'}))

    def get_parking_history(self, filters=None):
        """Get parking history with optional filters"""
        query = filters or {}
        return list(self.parking_records.find(query).sort('entry_time', -1))

    def save_rover_data(self, data):
        """Save rover telemetry data"""
        data['timestamp'] = datetime.now()
        return self.rover_data.insert_one(data)

    def get_rover_history(self, limit=100):
        """Get recent rover telemetry history"""
        return list(self.rover_data.find().sort('timestamp', -1).limit(limit))

    def create_operator(self, username, password_hash, name, role='operator'):
        """Create a new operator account"""
        operator = {
            'username': username,
            'password': password_hash,
            'name': name,
            'role': role,
            'created_at': datetime.now(),
            'last_login': None
        }
        return self.operators.insert_one(operator)

    def create_admin(self, username, password_hash, name):
        """Create a new admin account"""
        admin = {
            'username': username,
            'password': password_hash,
            'name': name,
            'role': 'admin',
            'created_at': datetime.now(),
            'last_login': None
        }
        return self.admins.insert_one(admin)

    def get_parking_stats(self):
        """Get current parking statistics"""
        total_slots = self.parking_slots.count_documents({})
        occupied = self.parking_slots.count_documents({'status': 'occupied'})
        reserved = self.parking_slots.count_documents({'status': 'reserved'})
        available = total_slots - occupied - reserved

        return {
            'total_slots': total_slots,
            'occupied': occupied,
            'reserved': reserved,
            'available': available
        }

    def get_zone_stats(self, lot_id):
        """Get parking statistics by zone"""
        pipeline = [
            {'$match': {'lot_id': lot_id}},
            {'$group': {
                '_id': '$zone',
                'total': {'$sum': 1},
                'occupied': {
                    '$sum': {'$cond': [{'$eq': ['$status', 'occupied']}, 1, 0]}
                }
            }}
        ]
        return list(self.parking_slots.aggregate(pipeline))

# Create database instance
db = Database() 

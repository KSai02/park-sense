# ParkSense - Smart Parking Management System

ParkSense is a comprehensive parking management system that uses QR codes and license plate recognition to manage vehicle entry and exit in parking lots.

## Features

- QR code-based vehicle registration
- License plate recognition at entry points
- Real-time parking slot management
- Admin dashboard with live parking status
- Rover-based slot verification
- Frequent visitor tracking

## Project Structure

```
parksense/
├── backend/          
├── frontend/         
├── models/          
└── README.md
```
## Usage

### Visitor Flow

1. Scan the QR code at the parking lot entrance
2. Fill in the registration form with vehicle details
3. Receive a QR code for exit
4. Show the QR code at exit point when leaving

### Admin Dashboard

1. Access the admin dashboard at `/admin`
2. View real-time parking slot status
3. Monitor vehicle entries and exits
4. Track rover verification status

## API Endpoints

### Vehicle Management
- POST `/api/vehicles/register` - Register new vehicle
- POST `/api/vehicles/exit/:licensePlate` - Record vehicle exit
- GET `/api/vehicles/:licensePlate` - Get vehicle details

### Parking Slots
- GET `/api/parking-slots` - Get all parking slots
- POST `/api/parking-slots/initialize` - Initialize parking slots
- PUT `/api/parking-slots/verify/:slotNumber` - Update slot status

### Admin
- GET `/api/admin/dashboard` - Get dashboard statistics
- GET `/api/admin/current-vehicles` - Get current vehicles
- GET `/api/admin/parking-status` - Get parking status
- GET `/api/admin/rover-status` - Get rover verification status

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

const express = require('express');
const router = express.Router();
const Vehicle = require('../models/Vehicle');
const ParkingSlot = require('../models/ParkingSlot');
const QRCode = require('qrcode');

// Register new vehicle entry
router.post('/register', async (req, res) => {
    try {
        const { licensePlate, mobileNumber, email } = req.body;
        
        // Check if vehicle is already parked
        const existingVehicle = await Vehicle.findOne({ 
            licensePlate, 
            isCurrentlyParked: true 
        });
        
        if (existingVehicle) {
            return res.status(400).json({ message: 'Vehicle is already parked' });
        }

        // Find an empty parking slot
        const emptySlot = await ParkingSlot.findOne({ isOccupied: false });
        if (!emptySlot) {
            return res.status(400).json({ message: 'No parking slots available' });
        }

        // Check if frequent visitor
        const visitCount = await Vehicle.countDocuments({ licensePlate });
        const isFrequentVisitor = visitCount >= 3;

        // Generate QR code data
        const qrData = {
            licensePlate,
            parkingSlot: emptySlot.slotNumber,
            entryTime: new Date()
        };

        const qrCode = await QRCode.toDataURL(JSON.stringify(qrData));

        // Create new vehicle entry
        const vehicle = new Vehicle({
            licensePlate,
            mobileNumber,
            email,
            parkingSlot: emptySlot.slotNumber,
            entryTime: new Date(),
            entryDate: new Date(),
            isFrequentVisitor,
            qrCode
        });

        await vehicle.save();

        // Update parking slot
        emptySlot.isOccupied = true;
        emptySlot.currentVehicle = vehicle._id;
        await emptySlot.save();

        res.status(201).json({
            message: 'Vehicle registered successfully',
            vehicle,
            qrCode
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Handle vehicle exit
router.post('/exit/:licensePlate', async (req, res) => {
    try {
        const vehicle = await Vehicle.findOne({ 
            licensePlate: req.params.licensePlate,
            isCurrentlyParked: true 
        });

        if (!vehicle) {
            return res.status(404).json({ message: 'Vehicle not found or already exited' });
        }

        // Update vehicle exit details
        vehicle.exitTime = new Date();
        vehicle.exitDate = new Date();
        vehicle.isCurrentlyParked = false;
        await vehicle.save();

        // Update parking slot
        const parkingSlot = await ParkingSlot.findOne({ slotNumber: vehicle.parkingSlot });
        if (parkingSlot) {
            parkingSlot.isOccupied = false;
            parkingSlot.currentVehicle = null;
            await parkingSlot.save();
        }

        res.json({ message: 'Vehicle exit recorded successfully', vehicle });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get vehicle details by license plate
router.get('/:licensePlate', async (req, res) => {
    try {
        const vehicle = await Vehicle.findOne({ licensePlate: req.params.licensePlate });
        if (!vehicle) {
            return res.status(404).json({ message: 'Vehicle not found' });
        }
        res.json(vehicle);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router; 
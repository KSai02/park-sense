const express = require('express');
const router = express.Router();
const Vehicle = require('../models/Vehicle');
const ParkingSlot = require('../models/ParkingSlot');

// Get dashboard statistics
router.get('/dashboard', async (req, res) => {
    try {
        const totalSlots = await ParkingSlot.countDocuments();
        const occupiedSlots = await ParkingSlot.countDocuments({ isOccupied: true });
        const currentVehicles = await Vehicle.countDocuments({ isCurrentlyParked: true });
        const frequentVisitors = await Vehicle.countDocuments({ isFrequentVisitor: true });

        res.json({
            totalSlots,
            occupiedSlots,
            availableSlots: totalSlots - occupiedSlots,
            currentVehicles,
            frequentVisitors
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get all current vehicles
router.get('/current-vehicles', async (req, res) => {
    try {
        const vehicles = await Vehicle.find({ isCurrentlyParked: true })
            .sort({ entryTime: -1 });
        res.json(vehicles);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get vehicle history
router.get('/vehicle-history/:licensePlate', async (req, res) => {
    try {
        const vehicles = await Vehicle.find({ licensePlate: req.params.licensePlate })
            .sort({ entryTime: -1 });
        res.json(vehicles);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get parking slot status
router.get('/parking-status', async (req, res) => {
    try {
        const slots = await ParkingSlot.find()
            .populate('currentVehicle')
            .sort({ slotNumber: 1 });
        res.json(slots);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get rover verification status
router.get('/rover-status', async (req, res) => {
    try {
        const vehicles = await Vehicle.find({ isCurrentlyParked: true })
            .sort({ lastVerifiedByRover: 1 });
        
        const verificationStatus = vehicles.map(vehicle => ({
            licensePlate: vehicle.licensePlate,
            parkingSlot: vehicle.parkingSlot,
            lastVerified: vehicle.lastVerifiedByRover,
            needsVerification: (new Date() - vehicle.lastVerifiedByRover) > (30 * 60 * 1000) // 30 minutes
        }));

        res.json(verificationStatus);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router; 
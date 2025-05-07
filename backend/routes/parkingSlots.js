const express = require('express');
const router = express.Router();
const ParkingSlot = require('../models/ParkingSlot');
const Vehicle = require('../models/Vehicle');

// Get all parking slots
router.get('/', async (req, res) => {
    try {
        const slots = await ParkingSlot.find().populate('currentVehicle');
        res.json(slots);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Initialize parking slots (admin only)
router.post('/initialize', async (req, res) => {
    try {
        const { numberOfSlots, slotNumber } = req.body;
        
        // If slotNumber is provided, create a single slot with that number
        if (slotNumber) {
            // Check if slot number already exists
            const existingSlot = await ParkingSlot.findOne({ slotNumber });
            if (existingSlot) {
                return res.status(400).json({ message: 'Slot number already exists' });
            }

            const newSlot = new ParkingSlot({
                slotNumber,
                isOccupied: false
            });
            await newSlot.save();
            return res.status(201).json({ message: 'Parking slot added successfully', slot: newSlot });
        }

        // If numberOfSlots is provided, create multiple slots
        if (numberOfSlots) {
            const slots = [];
            for (let i = 1; i <= numberOfSlots; i++) {
                slots.push({
                    slotNumber: `A${i}`,
                    isOccupied: false
                });
            }
            await ParkingSlot.insertMany(slots);
            return res.status(201).json({ message: 'Parking slots initialized successfully' });
        }

        res.status(400).json({ message: 'Either slotNumber or numberOfSlots must be provided' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Update slot status (for rover verification)
router.put('/verify/:slotNumber', async (req, res) => {
    try {
        const { isOccupied, licensePlate } = req.body;
        const slot = await ParkingSlot.findOne({ slotNumber: req.params.slotNumber });

        if (!slot) {
            return res.status(404).json({ message: 'Parking slot not found' });
        }

        // Update slot status
        slot.isOccupied = isOccupied;
        slot.lastUpdated = new Date();

        if (!isOccupied) {
            slot.currentVehicle = null;
        } else if (licensePlate) {
            const vehicle = await Vehicle.findOne({ licensePlate });
            if (vehicle) {
                slot.currentVehicle = vehicle._id;
                vehicle.lastVerifiedByRover = new Date();
                await vehicle.save();
            }
        }

        await slot.save();
        res.json(slot);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get slot details with vehicle information
router.get('/:slotNumber', async (req, res) => {
    try {
        const slot = await ParkingSlot.findOne({ slotNumber: req.params.slotNumber })
            .populate('currentVehicle');
        
        if (!slot) {
            return res.status(404).json({ message: 'Parking slot not found' });
        }
        
        res.json(slot);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router; 
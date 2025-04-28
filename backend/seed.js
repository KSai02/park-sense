import mongoose from 'mongoose';
import dotenv from 'dotenv';
import ParkingSlot from './models/ParkingSlot.js';
import connectDB from './config/db.js';

dotenv.config();
connectDB();

const seedSlots = async () => {
    await ParkingSlot.deleteMany();
    await ParkingSlot.insertMany([
        { slotNumber: 'A1', isOccupied: false },
        { slotNumber: 'A2', isOccupied: false },
        { slotNumber: 'A3', isOccupied: false }
    ]);
    console.log('Parking Slots Added!');
    process.exit();
};

seedSlots();

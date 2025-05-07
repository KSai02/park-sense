const mongoose = require('mongoose');

const vehicleSchema = new mongoose.Schema({
    licensePlate: {
        type: String,
        required: true,
        unique: true
    },
    mobileNumber: {
        type: String,
        required: true
    },
    email: {
        type: String,
        required: false
    },
    parkingSlot: {
        type: String,
        required: true
    },
    entryTime: {
        type: Date,
        required: true
    },
    entryDate: {
        type: Date,
        required: true
    },
    exitTime: {
        type: Date,
        default: null
    },
    exitDate: {
        type: Date,
        default: null
    },
    isFrequentVisitor: {
        type: Boolean,
        default: false
    },
    qrCode: {
        type: String,
        required: true
    },
    isCurrentlyParked: {
        type: Boolean,
        default: true
    },
    lastVerifiedByRover: {
        type: Date,
        default: Date.now
    }
});

module.exports = mongoose.model('Vehicle', vehicleSchema); 
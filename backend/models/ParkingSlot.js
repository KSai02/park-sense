import mongoose from 'mongoose';

const parkingSlotSchema = new mongoose.Schema({
  slotNumber: { type: String, required: true },
  isOccupied: { type: Boolean, default: false },
  currentVisitor: { type: mongoose.Schema.Types.ObjectId, ref: 'Visitor' }
});

export default mongoose.model('ParkingSlot', parkingSlotSchema);

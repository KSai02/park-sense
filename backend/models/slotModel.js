import mongoose from 'mongoose';

const slotSchema = new mongoose.Schema({
  slotNumber: { type: String, required: true },
  isOccupied: { type: Boolean, default: false },
  visitor: { type: mongoose.Schema.Types.ObjectId, ref: 'Visitor' },
});

export default mongoose.model('Slot', slotSchema);

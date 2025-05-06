import mongoose from 'mongoose';

const visitorSchema = new mongoose.Schema({
  mobileNumber: { type: String, required: true },
  email: { type: String },
  licensePlate: { type: String, required: true },
  suggestedSlot: { type: mongoose.Schema.Types.ObjectId, ref: 'Slot' }, // <-- ref must match model name
  qrCodeData: { type: String },
  entryTime: { type: Date, default: Date.now },
  exitTime: { type: Date },
  isFrequentVisitor: { type: Boolean, default: false },
  visitCompleted: { type: Boolean, default: false }
});

export default mongoose.model('Visitor', visitorSchema);

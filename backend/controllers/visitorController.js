import Visitor from '../models/Visitor.js';
import Slot from '../models/slotModel.js';  // Use 'Slot' here
import { generateQRCode } from '../utils/qrGenerator.js';

export const registerVisitor = async (req, res) => {
  const { mobileNumber, email, licensePlate } = req.body;
  try {
    // Find empty parking slot
    const emptySlot = await Slot.findOne({ isOccupied: false });
    if (!emptySlot) return res.status(400).json({ message: 'No parking slots available' });

    // Generate QR code for exit verification
    const qrData = `ExitVerification-${licensePlate}-${Date.now()}`;
    const qrCodeImage = await generateQRCode(qrData);

    // Create a new visitor
    const visitor = await Visitor.create({
      mobileNumber,
      email,
      licensePlate,
      suggestedSlot: emptySlot._id,  // Store the slot ID in the visitor record
      qrCodeData: qrCodeImage,
    });

    // Update Parking slot to mark it as occupied
    emptySlot.isOccupied = true;
    emptySlot.currentVisitor = visitor._id;  // Link the visitor to this slot
    await emptySlot.save();

    // Respond with success message and QR code
    res.status(201).json({
      message: `Slot ${emptySlot.slotNumber} Assigned`,
      qrCodeImage,
      slot: emptySlot.slotNumber
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

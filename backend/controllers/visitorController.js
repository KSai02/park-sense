import Visitor from '../models/Visitor.js';
import ParkingSlot from '../models/ParkingSlot.js';
import { generateQRCode } from '../utils/qrGenerator.js';

export const registerVisitor = async (req, res) => {
  const { mobileNumber, email, licensePlate } = req.body;
  try {
    // Find empty parking slot
    const emptySlot = await ParkingSlot.findOne({ isOccupied: false });
    if (!emptySlot) return res.status(400).json({ message: 'No parking slots available' });

    const qrData = `ExitVerification-${licensePlate}-${Date.now()}`;
    const qrCodeImage = await generateQRCode(qrData);

    const visitor = await Visitor.create({
      mobileNumber,
      email,
      licensePlate,
      suggestedSlot: emptySlot._id,
      qrCodeData: qrCodeImage,
    });

    // Update Parking slot
    emptySlot.isOccupied = true;
    emptySlot.currentVisitor = visitor._id;
    await emptySlot.save();

    res.status(201).json({
      message: `Slot ${emptySlot.slotNumber} Assigned`,
      qrCodeImage,
      slot: emptySlot.slotNumber
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

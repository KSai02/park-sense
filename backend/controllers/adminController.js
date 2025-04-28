import ParkingSlot from '../models/ParkingSlot.js';

export const getParkingSlots = async (req, res) => {
  try {
    const slots = await ParkingSlot.find().populate('currentVisitor');
    res.json(slots);
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

export const getSlotDetails = async (req, res) => {
  try {
    const slot = await ParkingSlot.findById(req.params.slotId).populate('currentVisitor');
    res.json(slot);
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

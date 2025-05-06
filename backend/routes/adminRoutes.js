import express from 'express';
import Slot from '../models/slotModel.js';
import Visitor from '../models/Visitor.js';

const router = express.Router();

// Get all slots with visitor details
router.get('/slots', async (req, res) => {
  try {
    const slots = await Slot.find().populate('visitor');
    res.json(slots);
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
});

// Add a new slot
router.post('/slots', async (req, res) => {
  try {
    const { slotNumber } = req.body;
    const newSlot = new Slot({ slotNumber });
    await newSlot.save();
    res.json({ message: 'Slot added successfully', slot: newSlot });
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
});

export default router;

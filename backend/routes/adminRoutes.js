import express from 'express';
import { getParkingSlots, getSlotDetails } from '../controllers/adminController.js';

const router = express.Router();

router.get('/slots', getParkingSlots);
router.get('/slot/:slotId', getSlotDetails);

export default router;

import express from 'express';
import { registerVisitor } from '../controllers/visitorController.js';

const router = express.Router();

router.post('/register', registerVisitor);

export default router;

const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const dotenv = require('dotenv');
const QRCode = require('qrcode');

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
dotenv.config();

// MongoDB Connection
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/parksense', {
    useNewUrlParser: true,
    useUnifiedTopology: true
})
.then(() => console.log('MongoDB Connected'))
.catch(err => console.log('MongoDB Connection Error:', err));

// Routes
const vehicleRoutes = require('./routes/vehicles');
const parkingSlotRoutes = require('./routes/parkingSlots');
const adminRoutes = require('./routes/admin');

app.use('/api/vehicles', vehicleRoutes);
app.use('/api/parking-slots', parkingSlotRoutes);
app.use('/api/admin', adminRoutes);

// Generate QR Code endpoint
app.post('/api/generate-qr', async (req, res) => {
    try {
        const { data } = req.body;
        const qrCode = await QRCode.toDataURL(JSON.stringify(data));
        res.json({ qrCode });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

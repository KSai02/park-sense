import React, { useState } from 'react';
import axios from 'axios';
import {
    Container,
    Paper,
    TextField,
    Button,
    Typography,
    Box,
    CircularProgress
} from '@mui/material';
import { QRCodeSVG } from 'qrcode.react';

const VisitorRegistration = () => {
    const [formData, setFormData] = useState({
        licensePlate: '',
        mobileNumber: '',
        email: ''
    });
    const [loading, setLoading] = useState(false);
    const [registrationData, setRegistrationData] = useState(null);
    const [error, setError] = useState('');

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const response = await axios.post('http://localhost:5000/api/vehicles/register', formData);
            setRegistrationData(response.data);
        } catch (error) {
            setError(error.response?.data?.message || 'An error occurred during registration');
        } finally {
            setLoading(false);
        }
    };

    if (registrationData) {
        return (
            <Container maxWidth="sm">
                <Paper elevation={3} sx={{ p: 4, mt: 4 }}>
                    <Typography variant="h5" gutterBottom>
                        Registration Successful!
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                        Your parking slot: {registrationData.vehicle.parkingSlot}
                    </Typography>
                    <Box sx={{ my: 3, display: 'flex', justifyContent: 'center' }}>
                        <QRCodeSVG value={registrationData.qrCode} size={200} />
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                        Please show this QR code at the exit point when leaving.
                    </Typography>
                </Paper>
            </Container>
        );
    }

    return (
        <Container maxWidth="sm">
            <Paper elevation={3} sx={{ p: 4, mt: 4 }}>
                <Typography variant="h5" gutterBottom>
                    Vehicle Registration
                </Typography>
                <form onSubmit={handleSubmit}>
                    <TextField
                        fullWidth
                        label="License Plate Number"
                        name="licensePlate"
                        value={formData.licensePlate}
                        onChange={handleChange}
                        required
                        margin="normal"
                    />
                    <TextField
                        fullWidth
                        label="Mobile Number"
                        name="mobileNumber"
                        value={formData.mobileNumber}
                        onChange={handleChange}
                        required
                        margin="normal"
                    />
                    <TextField
                        fullWidth
                        label="Email (Optional)"
                        name="email"
                        type="email"
                        value={formData.email}
                        onChange={handleChange}
                        margin="normal"
                    />
                    {error && (
                        <Typography color="error" sx={{ mt: 2 }}>
                            {error}
                        </Typography>
                    )}
                    <Button
                        type="submit"
                        variant="contained"
                        color="primary"
                        fullWidth
                        sx={{ mt: 3 }}
                        disabled={loading}
                    >
                        {loading ? <CircularProgress size={24} /> : 'Register'}
                    </Button>
                </form>
            </Paper>
        </Container>
    );
};

export default VisitorRegistration; 
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Container,
    Grid,
    Paper,
    Typography,
    Box,
    Card,
    CardContent,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    CircularProgress,
    Alert,
    TextField
} from '@mui/material';

const AdminDashboard = () => {
    const [dashboardData, setDashboardData] = useState(null);
    const [parkingSlots, setParkingSlots] = useState([]);
    const [selectedSlot, setSelectedSlot] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [addSlotDialog, setAddSlotDialog] = useState(false);
    const [newSlotNumber, setNewSlotNumber] = useState('');

    const fetchDashboardData = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/admin/dashboard');
            setDashboardData(response.data);
        } catch (error) {
            setError('Failed to fetch dashboard data');
        }
    };

    const fetchParkingSlots = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/admin/parking-status');
            setParkingSlots(response.data);
        } catch (error) {
            setError('Failed to fetch parking slots');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDashboardData();
        fetchParkingSlots();
        const interval = setInterval(() => {
            fetchParkingSlots();
        }, 30000); // Refresh every 30 seconds

        return () => clearInterval(interval);
    }, []);

    const handleSlotClick = (slot) => {
        setSelectedSlot(slot);
    };

    const handleCloseDialog = () => {
        setSelectedSlot(null);
    };

    const handleAddSlot = async () => {
        try {
            await axios.post('http://localhost:5000/api/parking-slots/initialize', {
                numberOfSlots: 1,
                slotNumber: newSlotNumber
            });
            setAddSlotDialog(false);
            setNewSlotNumber('');
            fetchParkingSlots();
            fetchDashboardData();
        } catch (error) {
            setError('Failed to add new parking slot');
        }
    };

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Container maxWidth="lg">
            <Box sx={{ mt: 4, mb: 4 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                    <Typography variant="h4">
                        Admin Dashboard
                    </Typography>
                    <Button 
                        variant="contained" 
                        color="primary"
                        onClick={() => setAddSlotDialog(true)}
                    >
                        Add Slot
                    </Button>
                </Box>

                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                    </Alert>
                )}
                
                {/* Statistics Cards */}
                <Grid container spacing={3} sx={{ mb: 4 }}>
                    <Grid item xs={12} sm={6} md={3}>
                        <Paper elevation={3} sx={{ p: 2 }}>
                            <Typography variant="h6">Total Slots</Typography>
                            <Typography variant="h4">{dashboardData?.totalSlots}</Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Paper elevation={3} sx={{ p: 2 }}>
                            <Typography variant="h6">Available Slots</Typography>
                            <Typography variant="h4">{dashboardData?.availableSlots}</Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Paper elevation={3} sx={{ p: 2 }}>
                            <Typography variant="h6">Current Vehicles</Typography>
                            <Typography variant="h4">{dashboardData?.currentVehicles}</Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Paper elevation={3} sx={{ p: 2 }}>
                            <Typography variant="h6">Frequent Visitors</Typography>
                            <Typography variant="h4">{dashboardData?.frequentVisitors}</Typography>
                        </Paper>
                    </Grid>
                </Grid>

                {/* Parking Slots Grid */}
                <Typography variant="h5" gutterBottom>
                    Parking Slots
                </Typography>
                <Grid container spacing={2}>
                    {parkingSlots.map((slot) => (
                        <Grid item xs={6} sm={4} md={3} key={slot.slotNumber}>
                            <Card
                                sx={{
                                    bgcolor: slot.isOccupied ? '#ffebee' : '#e8f5e9',
                                    cursor: 'pointer',
                                    '&:hover': {
                                        opacity: 0.8
                                    }
                                }}
                                onClick={() => handleSlotClick(slot)}
                            >
                                <CardContent>
                                    <Typography variant="h6" align="center">
                                        {slot.slotNumber}
                                    </Typography>
                                    <Typography variant="body2" align="center">
                                        {slot.isOccupied ? 'Occupied' : 'Available'}
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>
                    ))}
                </Grid>

                {/* Slot Details Dialog */}
                <Dialog open={Boolean(selectedSlot)} onClose={handleCloseDialog}>
                    {selectedSlot && (
                        <>
                            <DialogTitle>
                                Slot {selectedSlot.slotNumber} Details
                            </DialogTitle>
                            <DialogContent>
                                {selectedSlot.currentVehicle ? (
                                    <>
                                        <Typography variant="subtitle1">
                                            License Plate: {selectedSlot.currentVehicle.licensePlate}
                                        </Typography>
                                        <Typography variant="subtitle1">
                                            Mobile: {selectedSlot.currentVehicle.mobileNumber}
                                        </Typography>
                                        <Typography variant="subtitle1">
                                            Entry Time: {new Date(selectedSlot.currentVehicle.entryTime).toLocaleString()}
                                        </Typography>
                                        <Typography variant="subtitle1">
                                            Frequent Visitor: {selectedSlot.currentVehicle.isFrequentVisitor ? 'Yes' : 'No'}
                                        </Typography>
                                    </>
                                ) : (
                                    <Typography>No vehicle currently parked</Typography>
                                )}
                            </DialogContent>
                            <DialogActions>
                                <Button onClick={handleCloseDialog}>Close</Button>
                            </DialogActions>
                        </>
                    )}
                </Dialog>

                {/* Add Slot Dialog */}
                <Dialog open={addSlotDialog} onClose={() => setAddSlotDialog(false)}>
                    <DialogTitle>Add New Parking Slot</DialogTitle>
                    <DialogContent>
                        <TextField
                            autoFocus
                            margin="dense"
                            label="Slot Number"
                            type="text"
                            fullWidth
                            value={newSlotNumber}
                            onChange={(e) => setNewSlotNumber(e.target.value)}
                            placeholder="e.g., A1, B2, etc."
                        />
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={() => setAddSlotDialog(false)}>Cancel</Button>
                        <Button 
                            onClick={handleAddSlot} 
                            variant="contained" 
                            color="primary"
                            disabled={!newSlotNumber}
                        >
                            Add Slot
                        </Button>
                    </DialogActions>
                </Dialog>
            </Box>
        </Container>
    );
};

export default AdminDashboard; 
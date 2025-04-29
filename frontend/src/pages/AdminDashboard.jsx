import React, { useState, useEffect } from 'react';
import { Grid, Button, Modal, Typography, Card, CardContent } from '@mui/material';

const AdminDashboard = () => {
  const [slots, setSlots] = useState([]);
  const [open, setOpen] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState(null);

  useEffect(() => {
    const fetchSlots = async () => {
      const response = await fetch('http://localhost:5000/api/admin/slots');
      const data = await response.json();
      setSlots(data);
    };
    fetchSlots();
  }, []);

  const handleSlotClick = (slot) => {
    setSelectedSlot(slot);
    setOpen(true);
  };

  const handleClose = () => setOpen(false);

  return (
    <div style={{ padding: '20px' }}>
      <Typography variant="h4" align="center" gutterBottom>
        Admin Dashboard
      </Typography>
      <Grid container spacing={2} justifyContent="center">
        {slots.map((slot) => (
          <Grid item key={slot._id}>
            <Button
              variant="contained"
              color={slot.isOccupied ? 'error' : 'success'}
              onClick={() => handleSlotClick(slot)}
            >
              {slot.slotNumber}
            </Button>
          </Grid>
        ))}
      </Grid>

      <Modal open={open} onClose={handleClose}>
        <Card style={{ margin: '100px auto', width: '400px' }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              Vehicle Details for {selectedSlot?.slotNumber}
            </Typography>
            <Typography variant="body1">License Plate: {selectedSlot?.licensePlate}</Typography>
            <Typography variant="body1">Mobile Number: {selectedSlot?.mobileNumber}</Typography>
            <Typography variant="body1">Email: {selectedSlot?.email}</Typography>
            <Typography variant="body1">Entry Time: {selectedSlot?.entryTime}</Typography>
            <Typography variant="body1">Exit Time: {selectedSlot?.exitTime}</Typography>
          </CardContent>
        </Card>
      </Modal>
    </div>
  );
};

export default AdminDashboard;

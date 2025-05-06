import React, { useEffect, useState } from 'react';
import {
  Card, CardContent, Typography, Grid,
  Button, TextField, Dialog, DialogTitle, DialogContent
} from '@mui/material';

const AdminDashboard = () => {
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [newSlot, setNewSlot] = useState('');

  const fetchSlots = async () => {
    try {
      const res = await fetch('http://localhost:5000/api/admin/slots');
      const data = await res.json();
      setSlots(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddSlot = async () => {
    try {
      await fetch('http://localhost:5000/api/admin/slots', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slotNumber: newSlot }),
      });
      setNewSlot('');
      fetchSlots();
      setOpenDialog(false);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSlots();
  }, []);

  return (
    <div style={{ padding: '2rem' }}>
      <Typography variant="h4" gutterBottom>Admin Dashboard</Typography>
      <Button variant="contained" color="primary" onClick={() => setOpenDialog(true)}>
        Add New Slot
      </Button>

      <Grid container spacing={2} style={{ marginTop: '1rem' }}>
        {slots.map((slot) => (
          <Grid item xs={2} key={slot._id}>
            <Card
              style={{
                backgroundColor: slot.isOccupied ? '#f44336' : '#4caf50',
                cursor: 'pointer',
                color: 'white'
              }}
              onClick={() => setSelectedSlot(slot)}
            >
              <CardContent>
                <Typography variant="h6">{slot.slotNumber}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {selectedSlot && (
        <div style={{ marginTop: '2rem' }}>
          <Typography variant="h5">Slot: {selectedSlot.slotNumber}</Typography>
          {selectedSlot.visitor ? (
            <>
              <Typography>Mobile: {selectedSlot.visitor.mobileNumber}</Typography>
              <Typography>License: {selectedSlot.visitor.licensePlate}</Typography>
              <Typography>Email: {selectedSlot.visitor.email || 'N/A'}</Typography>
              <Typography>Entry Time: {new Date(selectedSlot.visitor.entryTime).toLocaleString()}</Typography>
            </>
          ) : (
            <Typography>No visitor assigned</Typography>
          )}
        </div>
      )}

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>Add Parking Slot</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Slot Number"
            value={newSlot}
            onChange={(e) => setNewSlot(e.target.value)}
            margin="dense"
          />
          <Button onClick={handleAddSlot} variant="contained" color="primary" style={{ marginTop: '1rem' }}>
            Add Slot
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;

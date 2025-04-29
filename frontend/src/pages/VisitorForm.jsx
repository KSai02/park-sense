import React, { useState } from 'react';
import { TextField, Button, Card, CardContent, Typography } from '@mui/material';
import { QRCodeCanvas } from 'qrcode.react';  // Correct import

const VisitorPage = () => {
  const [formData, setFormData] = useState({
    mobileNumber: '',
    licensePlate: '',
    email: '',
  });
  const [assignedSlot, setAssignedSlot] = useState('');
  const [qrCode, setQrCode] = useState('');

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    // Log form data to check what is being submitted
    console.log('Form Data:', formData);

    try {
      // Send POST request to backend API
      const response = await fetch('http://localhost:5000/api/visitor/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      // Parse the response
      const result = await response.json();
      console.log('Response from API:', result);

      // Check if the response is successful
      if (response.ok && result.message) {
        // Set assigned slot and QR code if successful
        setAssignedSlot(result.slot);
        setQrCode(result.qrCodeImage);
      } else {
        // Handle failure in the form submission
        alert('Failed to submit the form. Please try again.');
      }
    } catch (error) {
      // Catch and log any errors that occur during submission
      console.error('Error during form submission:', error);
      alert('Error during form submission. Please check the console for details.');
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <Card style={{ width: 400 }}>
        <CardContent>
          <Typography variant="h5" align="center" gutterBottom>
            Visitor Registration
          </Typography>
          <form onSubmit={handleSubmit}>
            <TextField
              label="Mobile Number"
              variant="outlined"
              fullWidth
              margin="normal"
              name="mobileNumber"
              value={formData.mobileNumber}
              onChange={handleInputChange}
              required
            />
            <TextField
              label="License Plate"
              variant="outlined"
              fullWidth
              margin="normal"
              name="licensePlate"
              value={formData.licensePlate}
              onChange={handleInputChange}
              required
            />
            <TextField
              label="Email (optional)"
              variant="outlined"
              fullWidth
              margin="normal"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
            />
            <Button type="submit" variant="contained" color="primary" fullWidth>
              Submit
            </Button>
          </form>

          {assignedSlot && (
            <div style={{ marginTop: '20px', textAlign: 'center' }}>
              <Typography variant="h6" color="textSecondary">
                Assigned Slot: {assignedSlot}
              </Typography>
              {/* Display QR Code */}
              <QRCodeCanvas value={qrCode} size={128} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default VisitorPage;

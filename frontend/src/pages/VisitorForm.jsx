import React, { useState } from 'react';
import { registerVisitor } from '../api';

const VisitorForm = () => {
  const [mobileNumber, setMobileNumber] = useState('');
  const [licensePlate, setLicensePlate] = useState('');
  const [email, setEmail] = useState('');
  const [assignedSlot, setAssignedSlot] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const { data } = await registerVisitor({ mobileNumber, licensePlate, email });
      setAssignedSlot(data);
    } catch (error) {
      console.error(error);
    }
  };

  if (assignedSlot) {
    return (
      <div className="text-center mt-10">
        <h1>Slot Assigned: {assignedSlot.slot}</h1>
        <img src={assignedSlot.qrCodeImage} alt="Exit QR Code" className="mx-auto mt-4" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-4 max-w-md mx-auto">
      <input type="text" placeholder="Mobile Number" value={mobileNumber} onChange={(e) => setMobileNumber(e.target.value)} required />
      <input type="text" placeholder="License Plate" value={licensePlate} onChange={(e) => setLicensePlate(e.target.value)} required />
      <input type="email" placeholder="Email (Optional)" value={email} onChange={(e) => setEmail(e.target.value)} />
      <button type="submit" className="bg-blue-500 text-white p-2 rounded">Submit</button>
    </form>
  );
};

export default VisitorForm;

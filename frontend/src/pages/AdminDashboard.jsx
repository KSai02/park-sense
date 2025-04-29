// import React, { useEffect, useState } from 'react';
// import { fetchSlots, fetchSlotDetails } from '../api';
// import SlotCard from '../components/SlotCard';

// const AdminDashboard = () => {
//   const [slots, setSlots] = useState([]);
//   const [selectedSlot, setSelectedSlot] = useState(null);

//   useEffect(() => {
//     const loadSlots = async () => {
//       const { data } = await fetchSlots();
//       setSlots(data);
//     };
//     loadSlots();
//   }, []);

//   const handleSlotClick = async (slotId) => {
//     const { data } = await fetchSlotDetails(slotId);
//     setSelectedSlot(data);
//   };

//   return (
//     <div className="p-4">
//       <h1 className="text-xl font-bold mb-4">Parking Slots</h1>
//       <div className="grid grid-cols-5 gap-2">
//         {slots.map((slot) => (
//           <SlotCard key={slot._id} slot={slot} onClick={() => handleSlotClick(slot._id)} />
//         ))}
//       </div>

//       {selectedSlot && (
//         <div className="mt-6 p-4 border rounded">
//           <h2 className="text-lg font-semibold mb-2">Visitor Details</h2>
//           {selectedSlot.currentVisitor ? (
//             <div>
//               <p>Mobile: {selectedSlot.currentVisitor.mobileNumber}</p>
//               <p>License: {selectedSlot.currentVisitor.licensePlate}</p>
//               <p>Email: {selectedSlot.currentVisitor.email}</p>
//             </div>
//           ) : (
//             <p>Slot is empty.</p>
//           )}
//         </div>
//       )}
//     </div>
//   );
// };

// export default AdminDashboard;
import React, { useEffect, useState } from 'react';
import axios from 'axios';

const AdminDashboard = () => {
  const [slots, setSlots] = useState([]);

  useEffect(() => {
    // Fetch parking slots from backend
    axios.get('http://localhost:5000/api/admin/slots')
      .then(response => {
        setSlots(response.data);
      })
      .catch(error => {
        console.log('Error fetching parking slots:', error);
      });
  }, []);

  const handleSlotClick = (slotId) => {
    // Fetch slot details when clicked
    axios.get(`http://localhost:5000/api/admin/slots/${slotId}`)
      .then(response => {
        alert('Visitor Details: ' + JSON.stringify(response.data));
      })
      .catch(error => {
        console.log('Error fetching slot details:', error);
      });
  };

  return (
    <div>
      <h1>Admin Dashboard</h1>
      <div className="slot-container">
        {slots.map((slot) => (
          <div
            key={slot._id}
            className={`slot ${slot.isOccupied ? 'occupied' : 'available'}`}
            onClick={() => handleSlotClick(slot._id)}
          >
            {slot.slotNumber}
          </div>
        ))}
      </div>
    </div>
  );
};

export default AdminDashboard;

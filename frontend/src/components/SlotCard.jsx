import React from 'react';

const SlotCard = ({ slot, onClick }) => {
  return (
    <div
      className={`p-2 border rounded cursor-pointer ${slot.isOccupied ? 'bg-red-400' : 'bg-green-400'}`}
      onClick={onClick}
    >
      Slot {slot.slotNumber}
    </div>
  );
};

export default SlotCard;

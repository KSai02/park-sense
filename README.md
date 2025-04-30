#  ParkSense - Smart Parking System

ParkSense is a smart parking management system built using the MERN stack. It uses camera & rover based license plate detection, real-time slot tracking, and QR code-based access to automate and optimize the parking experience for visitors and administrators.

##  Features

### Visitor Side:
-  Automatic license plate scanning at entry
-  QR code scan redirects to visitor registration form
-  Visitors enter mobile number, license plate, email (optional)
-  System auto-assigns an available parking slot
-  QR code generated on successful registration for exit
-  QR code scanned at exit to release the slot

### Admin Side:
-  Dashboard to view all slots (green = empty, red = occupied)
-  Click on any slot to view visitor and vehicle details
-  Logs entry/exit time and date for each vehicle
-  Rovers periodically verify actual parking slot usage using OCR

##  Tech Stack

- *Frontend:* React.js, Material UI
- *Backend:* Node.js, Express.js
- *Database:* MongoDB (with Mongoose)
- *QR Code:* qrcode.react
- *OCR & LPR:* Python + OpenCV (external integration)
- *Deployment:* Render / Vercel

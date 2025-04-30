from ultralytics import YOLO
import cv2

model=YOLO('best.pt')

# Make sure to call model.eval() to set it to evaluation mode
model.eval()

# Open the video file
cap = cv2.VideoCapture('car.mp4')  # Replace with your video file path

# Check if the video opened successfully
if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

# Set up the video writer (for saving the output video)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4
out = cv2.VideoWriter('output_video.mp4', fourcc, 30.0, (640, 480))  # Adjust resolution accordingly

while True:
    ret, frame = cap.read()
    
    if not ret:
        break  # End of video if no frame is read
    
    # Make predictions on the frame
    results = model(frame)  # Pass the frame through the loaded model
    
    # Render predictions on the frame
    frame_with_predictions = results.render()[0]  # This will render bounding boxes and labels on the frame

    # Display the frame with predictions
    cv2.imshow('Frame', frame_with_predictions)
    
    # Save the frame to output video (optional)
    out.write(frame_with_predictions)

    # Break on 'q' key press to exit early
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
out.release()  # If saving the video output
cv2.destroyAllWindows()

// frontend/src/CameraModal.jsx
import React, { useRef, useEffect, useState } from 'react';

function CameraModal({ onCapture, onClose }) {
  const videoRef = useRef(null);
  const [stream, setStream] = useState(null);

  useEffect(() => {
    // This function starts the camera
    async function getCameraStream() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { facingMode: 'environment' } // Prefers the rear camera on mobile
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setStream(stream);
      } catch (err) {
        console.error("Error accessing camera:", err);
        alert("Could not access camera. Please ensure you have given permission. You can still upload a file manually.");
        onClose();
      }
    }

    getCameraStream();

    // This is a cleanup function to stop the camera when the modal closes
    return () => {
      stream?.getTracks().forEach(track => track.stop());
    };
  }, []);

  const takePicture = () => {
    const video = videoRef.current;
    if (!video) return;

    // We use a canvas to draw the current frame from the video
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert the canvas image to a file object
    canvas.toBlob((blob) => {
      const file = new File([blob], "camera-capture.png", { type: "image/png" });
      onCapture(file); // Send the file back to the main App
      onClose();
    }, 'image/png');
  };

  return (
    <div className="modal-backdrop">
      <div className="camera-modal">
        <video ref={videoRef} autoPlay playsInline className="camera-feed"></video>
        <button onClick={takePicture} className="capture-button">Take Photo</button>
        <button onClick={onClose} className="cancel-button">Cancel</button>
      </div>
    </div>
  );
}

export default CameraModal;
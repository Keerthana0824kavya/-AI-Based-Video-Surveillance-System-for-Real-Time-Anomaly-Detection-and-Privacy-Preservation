import React, { useRef, useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Camera, Video, VideoOff, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';

const WebcamFeed = ({ onDetect, isSystemActive, setIsSystemActive }) => {
  const videoRef = useRef(null);
  const [isWebcamOn, setIsWebcamOn] = useState(false);
  const [error, setError] = useState(null);
  const { toast } = useToast();

  const stopWebcam = useCallback(() => {
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setIsWebcamOn(false);
    if (isSystemActive) {
      setIsSystemActive(false);
      toast({ title: "Webcam & System Deactivated", description: "Monitoring has stopped." });
    }
  }, [isSystemActive, setIsSystemActive, toast]);

  const startWebcam = async () => {
    if (isWebcamOn) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsWebcamOn(true);
      setIsSystemActive(true);
      setError(null);
      toast({ title: "Webcam Activated", description: "AI monitoring has started on your webcam feed." });
    } catch (err) {
      console.error("Error accessing webcam:", err);
      setError("Could not access webcam. Please check permissions and try again.");
      toast({ title: "Webcam Error", description: "Could not access webcam. Please check permissions.", variant: "destructive" });
      setIsWebcamOn(false);
      setIsSystemActive(false);
    }
  };

  useEffect(() => {
    let detectionInterval;
    if (isWebcamOn && isSystemActive) {
      detectionInterval = setInterval(() => {
        if (Math.random() < 0.1) { // Simulate detection
          onDetect({
            location: 'Local Environment',
            severity: 'Medium',
            type: 'Unusual Motion',
            camera: 'User Webcam',
            confidence: Math.floor(Math.random() * 30) + 60
          });
        }
      }, 5000);
    }
    return () => {
      clearInterval(detectionInterval);
    };
  }, [isWebcamOn, isSystemActive, onDetect]);

  useEffect(() => {
    // Cleanup function to stop webcam when component unmounts or tab changes
    return () => {
      stopWebcam();
    };
  }, [stopWebcam]);

  return (
    <div className="space-y-4">
      <div className="aspect-video bg-black rounded-lg overflow-hidden relative flex items-center justify-center">
        <video ref={videoRef} autoPlay playsInline muted className={`w-full h-full object-cover ${isWebcamOn ? 'block' : 'hidden'}`} />
        {!isWebcamOn && (
          <div className="text-center text-gray-400">
            <Camera className="w-16 h-16 mx-auto mb-4" />
            <p>Webcam is currently off</p>
          </div>
        )}
        {error && (
           <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 text-red-400 p-4">
             <AlertCircle className="w-10 h-10 mb-2" />
             <p className="text-center">{error}</p>
           </div>
        )}
      </div>
      <div className="flex justify-center space-x-4">
        {!isWebcamOn ? (
          <Button onClick={startWebcam} className="bg-green-600 hover:bg-green-700">
            <Video className="w-4 h-4 mr-2" /> Start Webcam
          </Button>
        ) : (
          <Button onClick={stopWebcam} variant="destructive">
            <VideoOff className="w-4 h-4 mr-2" /> Stop Webcam
          </Button>
        )}
      </div>
    </div>
  );
};

export default WebcamFeed;
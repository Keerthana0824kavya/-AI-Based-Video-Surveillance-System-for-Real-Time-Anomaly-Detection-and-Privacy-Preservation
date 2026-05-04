import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Shield, AlertTriangle, Activity, Video, FileVideo, LogOut, VideoOff, Bluetooth, Power } from 'lucide-react';
import VideoFeed from '@/components/VideoFeed';
import AlertPanel from '@/components/AlertPanel';
import NotificationSettings from '@/components/NotificationSettings';
import SystemStats from '@/components/SystemStats';
import { useToast } from '@/components/ui/use-toast';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import UploadedVideoPlayer from '@/components/UploadedVideoPlayer';
import WebcamFeed from '@/components/WebcamFeed';
import BluetoothCCTVModal from '@/components/BluetoothCCTVModal';
import emailjs from '@emailjs/browser';

const SurveillanceSystem = ({ onLogout }) => {
  const [isSystemActive, setIsSystemActive] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [uploadedVideo, setUploadedVideo] = useState(null);
  const [isBluetoothModalOpen, setIsBluetoothModalOpen] = useState(false);
  const [systemStats, setSystemStats] = useState({
    camerasOnline: 0,
    totalCameras: 4,
    alertsToday: 0,
    uptime: '00:00:00'
  });
  const { toast } = useToast();

  useEffect(() => {
    let interval;
    if (isSystemActive) {
      interval = setInterval(() => {
        setSystemStats(prev => {
          const parts = prev.uptime.split(':').map(Number);
          let [hours, minutes, seconds] = parts;
          seconds++;
          if (seconds >= 60) { seconds = 0; minutes++; }
          if (minutes >= 60) { minutes = 0; hours++; }
          return {
            ...prev,
            uptime: `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
          };
        });
      }, 1000);
    } else {
      setSystemStats(prev => ({ ...prev, uptime: '00:00:00' }));
    }
    return () => clearInterval(interval);
  }, [isSystemActive]);

  const handleSystemToggle = () => {
    const newStatus = !isSystemActive;
    setIsSystemActive(newStatus);
    setSystemStats(prev => ({
      ...prev,
      camerasOnline: newStatus ? prev.totalCameras : 0,
    }));
    toast({
      title: newStatus ? "System Activated" : "System Deactivated",
      description: newStatus ? "Live AI monitoring started successfully" : "Live surveillance monitoring stopped",
    });
  };

  const sendEmail = (alertData) => {
    const serviceID = import.meta.env.VITE_EMAILJS_SERVICE_ID;
    const templateID = import.meta.env.VITE_EMAILJS_TEMPLATE_ID;
    const publicKey = import.meta.env.VITE_EMAILJS_PUBLIC_KEY;

    if (!serviceID || !templateID || !publicKey || serviceID === 'YOUR_SERVICE_ID') {
      toast({
        title: "📧 EmailJS Not Configured",
        description: "Please follow the setup instructions to enable email notifications.",
        variant: "destructive",
      });
      return;
    }

    const templateParams = {
      to_email: 'bibhudattabehera10@gmail.com',
      alert_type: alertData.type,
      location: alertData.location,
      timestamp: alertData.timestamp,
      severity: alertData.severity,
      camera: alertData.camera,
      confidence: alertData.confidence,
      coordinates: alertData.latitude 
  ? `https://www.google.com/maps?q=${alertData.latitude},${alertData.longitude}`
  : 'Location not available'
    };

    emailjs.send(serviceID, templateID, templateParams)
      .then((response) => {
        console.log('SUCCESS!', response.status, response.text);
        toast({
          title: "📧 Email Sent Successfully",
          description: `Emergency notification sent to ${templateParams.to_email}.`,
        });
      })
      .catch((err) => {
        console.error('FAILED...', err);
        toast({
          title: "📧 Email Sending Failed",
          description: "Could not send email. Check your EmailJS settings and network.",
          variant: "destructive",
        });
      });
  };

  const createAlert = useCallback((alertData) => {
    const processAlert = (finalAlertData) => {
      const newAlert = { id: Date.now(), timestamp: new Date().toLocaleString(), ...finalAlertData };
      setAlerts(prev => [newAlert, ...prev.slice(0, 9)]);
      setSystemStats(prev => ({ ...prev, alertsToday: prev.alertsToday + 1 }));

      toast({
        title: "🚨 ANOMALY DETECTED!",
        description: `${newAlert.type} at ${newAlert.location}. Location captured.`,
      });

      sendEmail(newAlert);
    };

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          processAlert({ ...alertData, latitude, longitude });
        },
        () => processAlert(alertData),
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
      );
    } else {
      processAlert(alertData);
    }
  }, [toast]);

  const simulateAccidentDetection = () => {
    if (!isSystemActive) {
      toast({
        title: "System Offline",
        description: "Please activate the system to simulate detection.",
        variant: "destructive",
      });
      return;
    }
    createAlert({
      location: 'Highway 101, Mile Marker 45',
      severity: 'High',
      type: 'Vehicle Collision',
      camera: `CCTV ${Math.floor(Math.random() * 4) + 1}`,
      confidence: Math.floor(Math.random() * 20) + 80
    });
  };

  return (
    <>
      <BluetoothCCTVModal
        isOpen={isBluetoothModalOpen}
        setIsOpen={setIsBluetoothModalOpen}
        setSystemStats={setSystemStats}
      />
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="min-h-screen p-4 grid-pattern"
      >
        <div className="max-w-7xl mx-auto space-y-6">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-effect rounded-2xl p-6"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-blue-500/20 rounded-xl"><Shield className="w-8 h-8 text-blue-400" /></div>
                <div>
                  <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">AI Surveillance System</h1>
                  <p className="text-gray-300">Road Accident Detection & Emergency Response</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className={`flex items-center space-x-2 px-4 py-2 rounded-full ${isSystemActive ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  <Activity className="w-4 h-4" />
                  <span className="font-medium">{isSystemActive ? 'LIVE' : 'OFFLINE'}</span>
                </div>
                <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={handleSystemToggle} className={`px-4 py-3 rounded-xl font-medium transition-all text-white ${isSystemActive ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}`}>
                  <Power className="w-5 h-5" />
                </motion.button>
                <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={onLogout} className="px-4 py-3 bg-gray-600 hover:bg-gray-700 rounded-xl font-medium transition-all text-white">
                  <LogOut className="w-5 h-5" />
                </motion.button>
              </div>
            </div>
          </motion.div>

          <SystemStats stats={systemStats} isActive={isSystemActive} />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-effect rounded-2xl p-6"
              >
                <Tabs defaultValue="live">
                  <div className="flex flex-wrap items-center justify-between mb-6 gap-4">
                    <TabsList>
                      <TabsTrigger value="live"><Video className="w-4 h-4 mr-2" />CCTV Feeds</TabsTrigger>
                      <TabsTrigger value="webcam"><VideoOff className="w-4 h-4 mr-2" />Webcam</TabsTrigger>
                      <TabsTrigger value="upload"><FileVideo className="w-4 h-4 mr-2" />Analyze File</TabsTrigger>
                    </TabsList>
                    <div className="flex items-center space-x-2">
                      <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={() => setIsBluetoothModalOpen(true)} className="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg text-white font-medium transition-colors flex items-center">
                        <Bluetooth className="w-4 h-4 mr-2" /> Connect CCTV
                      </motion.button>
                      <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={simulateAccidentDetection} className="px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg text-white font-medium transition-colors">
                        Simulate Detection
                      </motion.button>
                    </div>
                  </div>

                  <TabsContent value="live">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {[1, 2, 3, 4].map((camera) => (<VideoFeed key={camera} cameraId={camera} isActive={isSystemActive} />))}
                    </div>
                  </TabsContent>
                  <TabsContent value="webcam">
                    <WebcamFeed onDetect={createAlert} isSystemActive={isSystemActive} setIsSystemActive={setIsSystemActive} />
                  </TabsContent>
                  <TabsContent value="upload">
                    <UploadedVideoPlayer uploadedVideo={uploadedVideo} setUploadedVideo={setUploadedVideo} onDetect={createAlert} />
                  </TabsContent>
                </Tabs>
              </motion.div>
            </div>

            <div className="space-y-6">
              <AlertPanel alerts={alerts} />
              <NotificationSettings />
            </div>
          </div>
        </div>
      </motion.div>
    </>
  );
};

export default SurveillanceSystem;
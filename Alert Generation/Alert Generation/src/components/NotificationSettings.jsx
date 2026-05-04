import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, Phone, MessageSquare, Settings, Bell, MapPin } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';

const NotificationSettings = () => {
  const [emailSettings, setEmailSettings] = useState({
    enabled: true,
    email: 'emergency@traffic.gov',
    highPriority: true,
    mediumPriority: true,
    lowPriority: false,
    includeLocation: true,
  });

  const { toast } = useToast();

  const handleSaveSettings = () => {
    localStorage.setItem('notificationSettings', JSON.stringify(emailSettings));
    
    toast({
      title: "Settings Saved",
      description: "Notification preferences updated successfully",
      duration: 3000,
    });
  };

  const handleTestNotification = () => {
    toast({
      title: "🧪 Test Notification Sent",
      description: `Test email sent to ${emailSettings.email}${emailSettings.includeLocation ? ' with location.' : '.'}`,
      duration: 3000,
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.4 }}
      className="glass-effect rounded-2xl p-6"
    >
      <div className="flex items-center space-x-3 mb-6">
        <Bell className="w-6 h-6 text-blue-400" />
        <h2 className="text-xl font-semibold">Notifications</h2>
      </div>

      <div className="space-y-6">
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <Mail className="w-5 h-5 text-green-400" />
            <h3 className="font-medium">Email Alerts</h3>
          </div>
          
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-gray-300 mb-2">Emergency Email</label>
              <input
                type="email"
                value={emailSettings.email}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="emergency@example.com"
              />
            </div>

            <div className="space-y-2">
              <p className="text-sm text-gray-300">Alert Levels</p>
              {[
                { key: 'highPriority', label: 'High Priority', color: 'text-red-400' },
                { key: 'mediumPriority', label: 'Medium Priority', color: 'text-yellow-400' },
                { key: 'lowPriority', label: 'Low Priority', color: 'text-green-400' }
              ].map(({ key, label, color }) => (
                <label key={key} className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={emailSettings[key]}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, [key]: e.target.checked }))}
                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className={`text-sm ${color}`}>{label}</span>
                </label>
              ))}
            </div>

             <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={emailSettings.includeLocation}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, includeLocation: e.target.checked }))}
                className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-300 flex items-center"><MapPin className="w-4 h-4 mr-2 text-blue-400" /> Include Live Location</span>
            </label>
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="font-medium flex items-center space-x-2">
            <Settings className="w-5 h-5 text-blue-400" />
            <span>Quick Actions</span>
          </h3>
          
          <div className="grid grid-cols-1 gap-2">
            <Button
              onClick={handleTestNotification}
              variant="outline"
              className="w-full bg-white/5 border-white/20 text-white hover:bg-white/10"
            >
              Send Test Email
            </Button>
            
            <Button
              onClick={handleSaveSettings}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white"
            >
              Save Settings
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="font-medium">Emergency Contacts</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center space-x-3 p-2 bg-white/5 rounded-lg">
              <Phone className="w-4 h-4 text-green-400" />
              <span className="text-gray-300">911 Emergency</span>
            </div>
            <div className="flex items-center space-x-3 p-2 bg-white/5 rounded-lg">
              <Mail className="w-4 h-4 text-blue-400" />
              <span className="text-gray-300">Traffic Control Center</span>
            </div>
            <div className="flex items-center space-x-3 p-2 bg-white/5 rounded-lg">
              <MessageSquare className="w-4 h-4 text-purple-400" />
              <span className="text-gray-300">Emergency Services</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default NotificationSettings;
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Clock, MapPin, Camera, TrendingUp, Compass } from 'lucide-react';

const AlertPanel = ({ alerts }) => {
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'High': return 'text-red-400 bg-red-500/20';
      case 'Medium': return 'text-yellow-400 bg-yellow-500/20';
      case 'Low': return 'text-green-400 bg-green-500/20';
      default: return 'text-gray-400 bg-gray-500/20';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.3 }}
      className="glass-effect rounded-2xl p-6"
    >
      <div className="flex items-center space-x-3 mb-6">
        <AlertTriangle className="w-6 h-6 text-red-400" />
        <h2 className="text-xl font-semibold">Recent Alerts</h2>
        <div className="bg-red-500/20 text-red-400 px-2 py-1 rounded-full text-sm font-medium">
          {alerts.length}
        </div>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        <AnimatePresence>
          {alerts.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-8"
            >
              <AlertTriangle className="w-12 h-12 text-gray-500 mx-auto mb-3" />
              <p className="text-gray-400">No alerts detected</p>
              <p className="text-gray-500 text-sm">System monitoring for anomalies</p>
            </motion.div>
          ) : (
            alerts.map((alert, index) => (
              <motion.div
                key={alert.id}
                initial={{ opacity: 0, y: -20, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 20, scale: 0.9 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white/5 rounded-xl p-4 border border-white/10 hover:bg-white/10 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(alert.severity)}`}>
                    {alert.severity}
                  </div>
                  <div className="flex items-center space-x-1 text-gray-400 text-xs">
                    <Clock className="w-3 h-3" />
                    <span>{alert.timestamp}</span>
                  </div>
                </div>

                <h3 className="font-semibold text-white mb-2">{alert.type}</h3>
                
                <div className="space-y-2 text-sm">
                  <div className="flex items-center space-x-2 text-gray-300">
                    <MapPin className="w-4 h-4" />
                    <span>{alert.location}</span>
                  </div>
                  
                  {alert.latitude && alert.longitude && (
                    <a 
                      href={`https://www.openstreetmap.org/?mlat=${alert.latitude}&mlon=${alert.longitude}#map=16/${alert.latitude}/${alert.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-2 text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      <Compass className="w-4 h-4" />
                      <span>{`${alert.latitude.toFixed(5)}, ${alert.longitude.toFixed(5)}`}</span>
                    </a>
                  )}

                  <div className="flex items-center space-x-2 text-gray-300">
                    <Camera className="w-4 h-4" />
                    <span>{alert.camera}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2 text-gray-300">
                    <TrendingUp className="w-4 h-4" />
                    <span>Confidence: {alert.confidence}%</span>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-white/10">
                  <div className="flex space-x-2">
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      className="px-3 py-1 bg-blue-500 hover:bg-blue-600 rounded-lg text-white text-xs font-medium transition-colors"
                    >
                      View Details
                    </motion.button>
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      className="px-3 py-1 bg-green-500 hover:bg-green-600 rounded-lg text-white text-xs font-medium transition-colors"
                    >
                      Mark Resolved
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default AlertPanel;
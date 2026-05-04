import React from 'react';
import { motion } from 'framer-motion';
import { Camera, AlertTriangle, Clock, Wifi } from 'lucide-react';

const SystemStats = ({ stats, isActive }) => {
  const statCards = [
    {
      icon: Camera,
      label: 'Cameras Online',
      value: `${stats.camerasOnline}/${stats.totalCameras}`,
      color: stats.camerasOnline === stats.totalCameras ? 'text-green-400' : 'text-yellow-400',
      bgColor: stats.camerasOnline === stats.totalCameras ? 'bg-green-500/20' : 'bg-yellow-500/20'
    },
    {
      icon: AlertTriangle,
      label: 'Alerts Today',
      value: stats.alertsToday,
      color: stats.alertsToday > 0 ? 'text-red-400' : 'text-gray-400',
      bgColor: stats.alertsToday > 0 ? 'bg-red-500/20' : 'bg-gray-500/20'
    },
    {
      icon: Clock,
      label: 'Live Uptime',
      value: stats.uptime,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/20'
    },
    {
      icon: Wifi,
      label: 'Live Status',
      value: isActive ? 'Active' : 'Inactive',
      color: isActive ? 'text-green-400' : 'text-red-400',
      bgColor: isActive ? 'bg-green-500/20' : 'bg-red-500/20'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards.map((stat, index) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className="glass-effect rounded-xl p-6"
        >
          <div className="flex items-center space-x-4">
            <div className={`p-3 rounded-xl ${stat.bgColor}`}>
              <stat.icon className={`w-6 h-6 ${stat.color}`} />
            </div>
            <div>
              <p className="text-gray-300 text-sm">{stat.label}</p>
              <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
};

export default SystemStats;
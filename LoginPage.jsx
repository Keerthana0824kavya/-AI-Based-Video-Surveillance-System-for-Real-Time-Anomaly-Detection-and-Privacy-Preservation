import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, Mail, Lock, LogIn } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/use-toast';

const LoginPage = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { toast } = useToast();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (email && password) {
      toast({
        title: "Login Successful",
        description: "Welcome back! Redirecting to dashboard...",
      });
      setTimeout(onLogin, 1000);
    } else {
      toast({
        title: "Login Failed",
        description: "Please enter both email and password.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 grid-pattern">
      <motion.div
        initial={{ opacity: 0, y: -50, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, type: 'spring' }}
      >
        <Card className="w-full max-w-md glass-effect">
          <CardHeader className="text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: 'spring', stiffness: 260, damping: 20 }}
              className="mx-auto mb-4 p-3 bg-blue-500/20 rounded-full w-fit"
            >
              <Shield className="w-10 h-10 text-blue-400" />
            </motion.div>
            <CardTitle className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              AI Surveillance System
            </CardTitle>
            <CardDescription className="text-gray-300">
              Secure Login
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="email" className="flex items-center text-gray-300">
                  <Mail className="w-4 h-4 mr-2" /> Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="user@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-white/10 border-white/20 text-white placeholder-gray-400 focus:ring-blue-500"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password"  className="flex items-center text-gray-300">
                  <Lock className="w-4 h-4 mr-2" /> Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-white/10 border-white/20 text-white placeholder-gray-400 focus:ring-blue-500"
                />
              </div>
              <Button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold">
                <LogIn className="w-5 h-5 mr-2" /> Secure Login
              </Button>
            </form>
          </CardContent>
          <CardFooter>
            <p className="text-xs text-gray-400 text-center w-full">
              © 2025 AI Surveillance Inc. All rights reserved.
            </p>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
};

export default LoginPage;

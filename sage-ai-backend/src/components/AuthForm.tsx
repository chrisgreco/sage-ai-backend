
import React, { useState } from 'react';
import { Eye, EyeOff, Mail, Lock, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/hooks/useAuth';

interface AuthFormProps {
  mode: 'login' | 'signup';
  onToggleMode: () => void;
}

const AuthForm: React.FC<AuthFormProps> = ({ mode, onToggleMode }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const { signIn, signUp } = useAuth();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (mode === 'signup') {
        const { error } = await signUp(email, password, displayName);
        if (error) {
          toast({
            title: "Sign up failed",
            description: error.message,
            variant: "destructive"
          });
        } else {
          toast({
            title: "Check your email",
            description: "We've sent you a confirmation link to complete your registration."
          });
        }
      } else {
        const { error } = await signIn(email, password);
        if (error) {
          toast({
            title: "Sign in failed",
            description: error.message,
            variant: "destructive"
          });
        }
      }
    } catch (error) {
      toast({
        title: "An error occurred",
        description: "Please try again later.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="backdrop-blur-md bg-white/80 border border-slate-200/50 rounded-2xl shadow-2xl shadow-slate-900/10 p-8 w-full max-w-md mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-slate-700 via-gray-800 to-slate-600 bg-clip-text text-transparent mb-3">
          {mode === 'login' ? 'Welcome Back' : 'Join Sage'}
        </h2>
        <p className="text-slate-600">
          {mode === 'login' 
            ? 'Sign in to continue your debates' 
            : 'Create your account to start debating'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {mode === 'signup' && (
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">Display Name</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
              <Input
                type="text"
                placeholder="Your display name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="pl-11 h-12 border-slate-200 bg-white/60 backdrop-blur-sm focus:border-slate-400 focus:ring-slate-400/20 text-slate-800 placeholder:text-slate-400"
                required
              />
            </div>
          </div>
        )}

        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
            <Input
              type="email"
              placeholder="your.email@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="pl-11 h-12 border-slate-200 bg-white/60 backdrop-blur-sm focus:border-slate-400 focus:ring-slate-400/20 text-slate-800 placeholder:text-slate-400"
              required
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">Password</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
            <Input
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="pl-11 pr-12 h-12 border-slate-200 bg-white/60 backdrop-blur-sm focus:border-slate-400 focus:ring-slate-400/20 text-slate-800 placeholder:text-slate-400"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
        </div>

        <Button
          type="submit"
          disabled={loading}
          className="w-full h-12 bg-gradient-to-r from-slate-600 via-gray-700 to-slate-600 hover:from-slate-700 hover:via-gray-800 hover:to-slate-700 text-white font-semibold rounded-xl shadow-lg shadow-slate-900/25 hover:shadow-xl hover:shadow-slate-900/30 transition-all duration-300 transform hover:scale-105"
        >
          {loading ? (
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              <span>Please wait...</span>
            </div>
          ) : (
            mode === 'login' ? 'Sign In' : 'Create Account'
          )}
        </Button>
      </form>

      <div className="mt-8 text-center">
        <button
          type="button"
          onClick={onToggleMode}
          className="text-slate-600 hover:text-slate-800 transition-colors font-medium"
        >
          {mode === 'login' 
            ? "Don't have an account? Sign up" 
            : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
};

export default AuthForm;

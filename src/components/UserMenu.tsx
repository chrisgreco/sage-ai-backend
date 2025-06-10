
import React from 'react';
import { LogOut, User, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/use-toast';

const UserMenu: React.FC = () => {
  const { user, signOut } = useAuth();
  const { toast } = useToast();

  const handleSignOut = async () => {
    const { error } = await signOut();
    if (error) {
      toast({
        title: "Sign out failed",
        description: error.message,
        variant: "destructive"
      });
    }
  };

  if (!user) return null;

  return (
    <div className="flex items-center space-x-3">
      <div className="glass-panel px-3 py-2 flex items-center space-x-2">
        <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-600 rounded-full flex items-center justify-center">
          <User className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-medium text-content-primary">
          {user.email}
        </span>
      </div>
      
      <Button
        onClick={handleSignOut}
        variant="ghost"
        size="sm"
        className="glass-button hover:bg-red-100 hover:text-red-600"
      >
        <LogOut className="w-4 h-4" />
      </Button>
    </div>
  );
};

export default UserMenu;

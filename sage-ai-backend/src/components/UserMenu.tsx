
import React, { useState, useEffect } from 'react';
import { LogOut, User, Sparkles, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/use-toast';
import { useProfileIcon } from '@/hooks/useProfileIcon';
import { supabase } from '@/integrations/supabase/client';

const UserMenu: React.FC = () => {
  const { user, signOut } = useAuth();
  const { toast } = useToast();
  const { generateProfileIcon, isGenerating } = useProfileIcon();
  const [profile, setProfile] = useState<any>(null);

  useEffect(() => {
    if (user) {
      fetchProfile();
    }
  }, [user]);

  const fetchProfile = async () => {
    if (!user) return;
    
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', user.id)
      .single();
    
    if (!error && data) {
      setProfile(data);
    }
  };

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

  const handleGenerateIcon = async () => {
    const avatarUrl = await generateProfileIcon();
    if (avatarUrl) {
      setProfile(prev => ({ ...prev, avatar_url: avatarUrl }));
    }
  };

  if (!user) return null;

  const displayName = profile?.display_name || user.email;
  const avatarUrl = profile?.avatar_url;

  return (
    <div className="flex items-center space-x-2 md:space-x-3">
      <div className="glass-panel px-2 md:px-3 py-2 flex items-center space-x-2">
        <Avatar className="w-7 h-7 md:w-8 md:h-8">
          {avatarUrl ? (
            <AvatarImage src={avatarUrl} alt={displayName} />
          ) : (
            <AvatarFallback className="bg-gradient-to-br from-purple-500 to-blue-600 text-white">
              <User className="w-3 h-3 md:w-4 md:h-4" />
            </AvatarFallback>
          )}
        </Avatar>
        <span className="text-xs md:text-sm font-medium text-content-primary max-w-[80px] md:max-w-none truncate">
          {displayName}
        </span>
      </div>
      
      <Button
        onClick={handleGenerateIcon}
        disabled={isGenerating}
        variant="ghost"
        size="sm"
        className="glass-button hover:bg-purple-100 p-2"
        title="Generate unique philosophy-themed profile icon"
      >
        {isGenerating ? (
          <RefreshCw className="w-3 h-3 md:w-4 md:h-4 animate-spin" />
        ) : (
          <Sparkles className="w-3 h-3 md:w-4 md:h-4" />
        )}
      </Button>
      
      <Button
        onClick={handleSignOut}
        variant="ghost"
        size="sm"
        className="glass-button hover:bg-red-100 hover:text-red-600 p-2"
      >
        <LogOut className="w-3 h-3 md:w-4 md:h-4" />
      </Button>
    </div>
  );
};

export default UserMenu;

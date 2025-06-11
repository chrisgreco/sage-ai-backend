
import { useState } from 'react';
import { useAuth } from './useAuth';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from './use-toast';

export const useProfileIcon = () => {
  const [isGenerating, setIsGenerating] = useState(false);
  const { user } = useAuth();
  const { toast } = useToast();

  const generateProfileIcon = async () => {
    if (!user) {
      toast({
        title: "Error",
        description: "You must be logged in to generate a profile icon",
        variant: "destructive"
      });
      return null;
    }

    setIsGenerating(true);
    
    try {
      const { data, error } = await supabase.functions.invoke('generate-profile-icon', {
        body: { userId: user.id }
      });

      if (error) {
        throw error;
      }

      toast({
        title: "Success!",
        description: "Your unique philosophy-themed profile icon has been generated",
      });

      return data.avatar_url;
    } catch (error) {
      console.error('Error generating profile icon:', error);
      toast({
        title: "Generation failed",
        description: "Failed to generate profile icon. Please try again.",
        variant: "destructive"
      });
      return null;
    } finally {
      setIsGenerating(false);
    }
  };

  return {
    generateProfileIcon,
    isGenerating
  };
};

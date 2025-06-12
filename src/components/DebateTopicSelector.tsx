
import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Loader2, MessageSquare } from 'lucide-react';
import { useBackendAPI } from '@/hooks/useBackendAPI';

interface DebateTopicSelectorProps {
  onTopicSelected: (topic: string, roomName: string) => void;
}

const popularTopics = [
  "AI Ethics in Education",
  "Climate Change Solutions",
  "Universal Basic Income",
  "Future of Remote Work",
  "Social Media Regulation",
  "Space Exploration Priorities"
];

const DebateTopicSelector: React.FC<DebateTopicSelectorProps> = ({ onTopicSelected }) => {
  const [customTopic, setCustomTopic] = useState('');
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const { createDebate, isLoading, error } = useBackendAPI();

  const handleTopicSelect = async (topic: string) => {
    try {
      setSelectedTopic(topic);
      const response = await createDebate(topic);
      onTopicSelected(topic, response.room_name);
    } catch (err) {
      console.error('Failed to create debate:', err);
      setSelectedTopic(null);
    }
  };

  const handleCustomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (customTopic.trim()) {
      await handleTopicSelect(customTopic.trim());
    }
  };

  return (
    <Card className="glass-panel max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <MessageSquare className="w-5 h-5 text-silver-600" />
          <span>Choose Your Debate Topic</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <div className="p-3 rounded-lg bg-red-100 border border-red-200">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Popular Topics */}
        <div>
          <Label className="text-sm font-medium text-content-primary mb-3 block">
            Popular Topics
          </Label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {popularTopics.map((topic) => (
              <Button
                key={topic}
                variant="outline"
                className="glass-button text-left h-auto p-3 justify-start hover:bg-silver-50"
                onClick={() => handleTopicSelect(topic)}
                disabled={isLoading}
              >
                {isLoading && selectedTopic === topic ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : null}
                <span className="text-sm">{topic}</span>
              </Button>
            ))}
          </div>
        </div>

        {/* Custom Topic */}
        <div>
          <Label className="text-sm font-medium text-content-primary mb-3 block">
            Or Enter Your Own Topic
          </Label>
          <form onSubmit={handleCustomSubmit} className="flex space-x-2">
            <Input
              value={customTopic}
              onChange={(e) => setCustomTopic(e.target.value)}
              placeholder="Enter a debate topic..."
              className="glass-panel flex-1"
              disabled={isLoading}
            />
            <Button 
              type="submit" 
              disabled={!customTopic.trim() || isLoading}
              className="glass-button"
            >
              {isLoading && selectedTopic === customTopic ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Start Debate'
              )}
            </Button>
          </form>
        </div>
      </CardContent>
    </Card>
  );
};

export default DebateTopicSelector;

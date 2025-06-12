
import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Loader2, MessageSquare, AlertCircle, RefreshCw, Coffee } from 'lucide-react';
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
  const [backendHealth, setBackendHealth] = useState<boolean | null>(null);
  const { createDebate, checkHealth, isLoading, error, isWarming } = useBackendAPI();

  // Check backend health periodically while warming
  useEffect(() => {
    const healthCheck = async () => {
      const isHealthy = await checkHealth();
      setBackendHealth(isHealthy);
    };

    // Initial health check
    healthCheck();

    // If warming, check more frequently
    if (isWarming) {
      const interval = setInterval(healthCheck, 3000);
      return () => clearInterval(interval);
    }
  }, [checkHealth, isWarming]);

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

  const handleRetry = async () => {
    const isHealthy = await checkHealth();
    setBackendHealth(isHealthy);
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
        {/* Backend Warming Alert */}
        {isWarming && (
          <Alert>
            <Coffee className="h-4 w-4" />
            <AlertDescription>
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Server is waking up... This may take 30-60 seconds on first visit.</span>
              </div>
            </AlertDescription>
          </Alert>
        )}

        {/* Backend Status Alert */}
        {!isWarming && backendHealth === false && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>Unable to connect to the debate server. The server may be starting up - please wait a moment and try again.</span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRetry}
                className="ml-2"
              >
                <RefreshCw className="w-3 h-3 mr-1" />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* API Error Alert */}
        {error && !isWarming && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>{error}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRetry}
                className="ml-2"
              >
                <RefreshCw className="w-3 h-3 mr-1" />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
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
                disabled={isLoading || backendHealth === false || isWarming}
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
              disabled={isLoading || backendHealth === false || isWarming}
            />
            <Button 
              type="submit" 
              disabled={!customTopic.trim() || isLoading || backendHealth === false || isWarming}
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

        {/* Backend Status Indicator */}
        {backendHealth !== null && !isWarming && (
          <div className="text-xs text-content-secondary text-center">
            Server Status: {backendHealth ? (
              <span className="text-green-600">Connected</span>
            ) : (
              <span className="text-red-600">Disconnected</span>
            )}
          </div>
        )}

        {isWarming && (
          <div className="text-xs text-content-secondary text-center">
            Server Status: <span className="text-yellow-600">Warming up...</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default DebateTopicSelector;

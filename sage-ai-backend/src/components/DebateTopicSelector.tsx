import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Loader2, MessageSquare, AlertCircle, RefreshCw, Coffee, Brain } from 'lucide-react';
import { useBackendAPI } from '@/hooks/useBackendAPI';

interface DebateTopicSelectorProps {
  onTopicSelected: (topic: string, roomName: string) => void;
}

const popularTopics = [
  "Should AI have rights and legal personhood?",
  "Is social media destroying democracy?",
  "Should we colonize Mars or fix Earth first?",
  "Is remote work the future of employment?",
  "Should genetic engineering be regulated globally?",
  "Is cryptocurrency the future of money?",
  "Should universal basic income be implemented?",
  "Is nuclear energy safer than renewable energy?",
  "Should space exploration be privatized?",
  "Is artificial intelligence a threat to humanity?",
  "Should social media algorithms be regulated?",
  "Is climate change action moving too slowly?"
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
    <div className="space-y-6">
      <Card className="glass-panel">
        <CardHeader className="text-center">
          <CardTitle className="flex items-center justify-center gap-2 text-content-primary">
            <Brain className="w-6 h-6" />
            Choose Your Debate Topic
          </CardTitle>
          <p className="text-sm text-content-secondary">
            Select a topic to start a moderated debate with AI facilitators
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Backend Status */}
          {backendHealth === false && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>
                  {isWarming 
                    ? 'Debate server is warming up. This may take 1-2 minutes...' 
                    : 'Unable to connect to debate server. Please try again.'}
                </span>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleRetry}
                  disabled={isLoading}
                >
                  <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {isWarming && (
            <Alert>
              <Coffee className="h-4 w-4" />
              <AlertDescription>
                Server is warming up... Please wait while we prepare the AI moderators.
              </AlertDescription>
            </Alert>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Popular Topics Grid */}
          <div>
            <Label className="text-sm font-medium text-content-primary mb-3 block">
              🤖 AI Moderator Ready Topics
            </Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {popularTopics.map((topic) => (
                <Button
                  key={topic}
                  variant="outline"
                  className="h-auto p-3 text-left justify-start glass-button hover:bg-white/60"
                  onClick={() => handleTopicSelect(topic)}
                  disabled={isLoading || selectedTopic === topic || backendHealth === false}
                >
                  {selectedTopic === topic ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm">Starting...</span>
                    </div>
                  ) : (
                    <span className="text-sm leading-relaxed">{topic}</span>
                  )}
                </Button>
              ))}
            </div>
          </div>

          {/* Custom Topic */}
          <div>
            <Label htmlFor="custom-topic" className="text-sm font-medium text-content-primary mb-2 block">
              💭 Or Create Your Own Topic
            </Label>
            <form onSubmit={handleCustomSubmit} className="space-y-3">
              <Input
                id="custom-topic"
                type="text"
                placeholder="Enter your debate topic..."
                value={customTopic}
                onChange={(e) => setCustomTopic(e.target.value)}
                className="glass-input"
                disabled={isLoading || backendHealth === false}
              />
              <Button
                type="submit"
                disabled={!customTopic.trim() || isLoading || backendHealth === false}
                className="w-full glass-button bg-blue-500 text-white hover:bg-blue-600"
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating Debate Room...</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    <span>Start Custom Debate</span>
                  </div>
                )}
              </Button>
            </form>
          </div>

          {/* AI Moderators Preview */}
          <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
            <h3 className="text-sm font-semibold text-content-primary mb-2 flex items-center gap-2">
              <Brain className="w-4 h-4" />
              Your AI Debate Moderators
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 text-xs">
              <div className="text-center p-2 bg-white/50 rounded">
                <div className="font-medium">Socrates</div>
                <div className="text-gray-600">Clarifier</div>
              </div>
              <div className="text-center p-2 bg-white/50 rounded">
                <div className="font-medium">Solon</div>
                <div className="text-gray-600">Rule Enforcer</div>
              </div>
              <div className="text-center p-2 bg-white/50 rounded">
                <div className="font-medium">Buddha</div>
                <div className="text-gray-600">Peacekeeper</div>
              </div>
              <div className="text-center p-2 bg-white/50 rounded">
                <div className="font-medium">Hermes</div>
                <div className="text-gray-600">Summarizer</div>
              </div>
              <div className="text-center p-2 bg-white/50 rounded">
                <div className="font-medium">Aristotle</div>
                <div className="text-gray-600">Fact-Checker</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DebateTopicSelector;


import React, { useState, useEffect } from 'react';
import { Brain, Eye, EyeOff, RefreshCcw } from 'lucide-react';
import { useAIModeration } from '@/hooks/useAIModeration';
import { Button } from './ui/button';
import { Tooltip } from './ui/tooltip';

interface AIModerationPanelProps {
  roomId: string;
  isWebRTCConnected?: boolean;
  onAudioData?: (callback: (audioData: Float32Array) => void) => void;
}

const AIModerationPanel: React.FC<AIModerationPanelProps> = ({ 
  roomId, 
  isWebRTCConnected = false,
  onAudioData 
}) => {
  const [agents, setAgents] = useState([
    { 
      name: 'Socrates', 
      role: 'Clarifier', 
      active: true,
      persona: 'Ask clarifying questions when assumptions are made or logic jumps occur'
    },
    { 
      name: 'Solon', 
      role: 'Rule Enforcer', 
      active: true,
      persona: 'Enforce debate rules and ensure fair turn-taking'
    },
    { 
      name: 'Buddha', 
      role: 'Peacekeeper', 
      active: true,
      persona: 'Monitor tone and diffuse conflict with empathy'
    },
    { 
      name: 'Hermes', 
      role: 'Summarizer', 
      active: false,
      persona: 'Provide summaries and logical transitions during breaks'
    },
    { 
      name: 'Aristotle', 
      role: 'Fact-Checker', 
      active: true,
      persona: 'Request sources for factual claims and assess evidence'
    }
  ]);

  const {
    aiConnected,
    aiConnecting,
    activeAgent,
    transcript,
    error,
    sendAudioToAI,
    connectToAI,
    disconnectFromAI
  } = useAIModeration({
    roomId,
    isConnected: isWebRTCConnected,
    agents
  });

  // Set up the audio callback when AI connection is ready and callback is provided
  useEffect(() => {
    console.log('AIModerationPanel: Setting up audio callback', { 
      onAudioData: !!onAudioData, 
      aiConnected, 
      sendAudioToAI: !!sendAudioToAI 
    });
    
    if (onAudioData && sendAudioToAI) {
      console.log('AIModerationPanel: Registering audio callback');
      onAudioData(sendAudioToAI);
    }
  }, [onAudioData, aiConnected, sendAudioToAI]);

  const toggleAgent = (agentName: string) => {
    setAgents(prev => prev.map(agent => 
      agent.name === agentName 
        ? { ...agent, active: !agent.active }
        : agent
    ));
  };

  const handleReconnect = () => {
    console.log('Manual reconnection requested');
    disconnectFromAI();
    setTimeout(() => {
      connectToAI();
    }, 500);
  };

  return (
    <div className="space-y-4">
      {/* AI Status */}
      <div className="glass-panel p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-content-primary">
            AI Moderation
          </h3>
          <div className={`flex items-center space-x-2 text-sm ${
            aiConnected ? 'text-green-600' : aiConnecting ? 'text-yellow-600' : 'text-red-600'
          }`}>
            <Brain className="w-4 h-4" />
            <span>
              {aiConnecting ? 'Connecting...' : aiConnected ? 'Online' : 'Offline'}
            </span>
          </div>
        </div>
        
        {error && (
          <div className="text-sm text-red-600 mb-3 p-2 bg-red-50 rounded">
            {error}
            <div className="mt-2">
              <Button 
                size="sm" 
                variant="outline" 
                onClick={handleReconnect}
                className="flex items-center space-x-1"
              >
                <RefreshCcw className="w-3 h-3" />
                <span>Reconnect</span>
              </Button>
            </div>
          </div>
        )}

        {activeAgent && (
          <div className="text-sm text-blue-600 mb-3 p-2 bg-blue-50 rounded">
            {activeAgent} is moderating...
          </div>
        )}

        {isWebRTCConnected && aiConnected && (
          <div className="text-sm text-green-600 mb-3 p-2 bg-green-50 rounded">
            Ready to moderate your debate
          </div>
        )}
        
        {/* Debug info */}
        <div className="text-xs text-content-muted mt-2 p-2 bg-gray-50 rounded">
          WebRTC: {isWebRTCConnected ? 'Connected' : 'Disconnected'} | 
          AI: {aiConnected ? 'Connected' : aiConnecting ? 'Connecting' : 'Offline'} | 
          Transcript entries: {transcript.length}
        </div>
      </div>

      {/* AI Moderators */}
      <div className="glass-panel p-4">
        <h3 className="text-lg font-semibold text-content-primary mb-3">
          AI Moderators
        </h3>
        <div className="space-y-3">
          {agents.map((agent) => (
            <div key={agent.name} className="agent-slot">
              <div className="flex items-center justify-between mb-1">
                <div>
                  <p className="text-sm font-medium text-content-primary">
                    {agent.name}
                  </p>
                  <p className="text-xs text-content-muted">{agent.role}</p>
                </div>
                <Tooltip content={agent.active ? 'Disable Agent' : 'Enable Agent'}>
                  <button
                    onClick={() => toggleAgent(agent.name)}
                    className={`p-1 rounded transition-colors ${
                      agent.active 
                        ? 'text-green-600 hover:bg-green-50' 
                        : 'text-gray-400 hover:bg-gray-50'
                    }`}
                  >
                    {agent.active ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  </button>
                </Tooltip>
              </div>
              <p className="text-xs text-content-secondary leading-relaxed">
                {agent.persona}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Live Transcript */}
      <div className="glass-panel p-4">
        <h3 className="text-lg font-semibold text-content-primary mb-3">
          Live Transcript
        </h3>
        <div className="space-y-2 max-h-60 overflow-y-auto">
          {transcript.length === 0 ? (
            <p className="text-sm text-content-muted italic">
              {isWebRTCConnected && aiConnected 
                ? "Start speaking to see transcript..."
                : "Connect audio and AI to see transcript..."
              }
            </p>
          ) : (
            transcript.map((entry, index) => (
              <div key={index} className="text-sm">
                <span className={`font-medium ${
                  entry.speaker.includes('AI') || agents.some(a => a.name === entry.speaker)
                    ? 'text-blue-600' 
                    : 'text-content-primary'
                }`}>
                  {entry.speaker}:
                </span>
                <span className="text-content-secondary ml-2">
                  {entry.text}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default AIModerationPanel;

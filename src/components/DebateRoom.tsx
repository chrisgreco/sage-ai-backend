import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Settings, ArrowLeft } from 'lucide-react';
import SageLogo from './SageLogo';
import WebRTCAudioRoom from './WebRTCAudioRoom';
import AIModerationPanel from './AIModerationPanel';
import DebateTopicSelector from './DebateTopicSelector';
import UserMenu from './UserMenu';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { useAuth } from '@/hooks/useAuth';

const DebateRoom: React.FC = () => {
  // Move all hooks to the top, before any conditional returns
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [showSettings, setShowSettings] = useState(false);
  const [isWebRTCConnected, setIsWebRTCConnected] = useState(false);
  const [lastAudioTimestamp, setLastAudioTimestamp] = useState<number | null>(null);
  const [debateTopic, setDebateTopic] = useState<string | null>(null);
  const [roomName, setRoomName] = useState<string | null>(null);
  const aiModerationCallbackRef = useRef<((audioData: Float32Array) => void) | null>(null);

  // AI Moderators state
  const [aiAgentsActive, setAiAgentsActive] = useState(false);
  const [launchingAgents, setLaunchingAgents] = useState(false);
  const [stoppingAgents, setStoppingAgents] = useState(false);

  // AI Agent personalities
  const aiAgents = [
    { name: "Socrates", role: "Clarifier", status: aiAgentsActive, description: "Asks probing questions to clarify positions" },
    { name: "Solon", role: "Rule Enforcer", status: aiAgentsActive, description: "Maintains debate structure and civility" },
    { name: "Buddha", role: "Peacekeeper", status: aiAgentsActive, description: "Promotes understanding and reduces conflict" },
    { name: "Hermes", role: "Summarizer", status: aiAgentsActive, description: "Synthesizes key points and transitions" },
    { name: "Aristotle", role: "Fact-Checker", status: aiAgentsActive, description: "Verifies claims and provides evidence" }
  ];

  const handleLeaveRoom = () => {
    navigate('/');
  };

  const handleLogoClick = () => {
    navigate('/');
  };

  const handleTopicSelected = (topic: string, generatedRoomName: string) => {
    console.log('Topic selected:', topic, 'Room:', generatedRoomName);
    setDebateTopic(topic);
    setRoomName(generatedRoomName);
  };

  const handleBackToTopicSelection = () => {
    setDebateTopic(null);
    setRoomName(null);
    setIsWebRTCConnected(false);
    // Stop AI agents when leaving room
    if (aiAgentsActive) {
      stopAIAgents();
    }
  };

  // Launch AI Agents
  const launchAIAgents = async () => {
    if (!roomName || !debateTopic) return;
    
    setLaunchingAgents(true);
    try {
      const response = await fetch('https://sage-ai-backend-l0en.onrender.com/launch-ai-agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          room_name: roomName,
          topic: debateTopic
        })
      });
      
      if (response.ok) {
        setAiAgentsActive(true);
        console.log('AI Agents launched successfully for topic:', debateTopic);
      } else {
        console.error('Failed to launch AI agents:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to launch AI agents:', error);
    }
    setLaunchingAgents(false);
  };

  // Stop AI Agents
  const stopAIAgents = async () => {
    if (!roomName) return;
    
    setStoppingAgents(true);
    try {
      const response = await fetch('https://sage-ai-backend-l0en.onrender.com/ai-agents/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_name: roomName })
      });
      
      if (response.ok) {
        setAiAgentsActive(false);
        console.log('AI Agents stopped successfully');
      } else {
        console.error('Failed to stop AI agents:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to stop AI agents:', error);
    }
    setStoppingAgents(false);
  };

  const handleAudioData = (audioData: Float32Array) => {
    // Update timestamp to track when we last received audio
    setLastAudioTimestamp(Date.now());
    
    // Forward audio data to AI moderation if available
    if (aiModerationCallbackRef.current) {
      console.log('DebateRoom: Forwarding audio to AI moderation, length:', audioData.length);
      aiModerationCallbackRef.current(audioData);
    } else {
      console.warn('DebateRoom: AI moderation callback not available');
    }
  };

  const handleAIModerationReady = (callback: (audioData: Float32Array) => void) => {
    console.log('DebateRoom: AI moderation callback registered');
    aiModerationCallbackRef.current = callback;
  };

  const handleWebRTCConnectionChange = (connected: boolean) => {
    console.log('DebateRoom: WebRTC connection changed:', connected);
    setIsWebRTCConnected(connected);
  };

  // Monitor audio activity
  useEffect(() => {
    if (!lastAudioTimestamp) return;
    
    const intervalId = setInterval(() => {
      const now = Date.now();
      if (lastAudioTimestamp && now - lastAudioTimestamp > 5000) {
        console.log('DebateRoom: No audio received in the last 5 seconds');
      }
    }, 5000);
    
    return () => clearInterval(intervalId);
  }, [lastAudioTimestamp]);

  // Show topic selector if no topic is selected
  if (!debateTopic || !roomName) {
    return (
      <div className="min-h-screen relative overflow-hidden">
        {/* Header */}
        <div className="glass-panel-elevated sticky top-0 z-50 mx-2 md:mx-3 mt-1 md:mt-1.5 mb-2 md:mb-3 fade-in-up">
          <div className="max-w-md mx-auto md:max-w-4xl px-2.5 md:px-4 py-0.5 md:py-1">
            <div className="flex items-center justify-between">
              <button onClick={handleLogoClick} className="hover:opacity-80 transition-opacity">
                <SageLogo size="sm" className="md:w-auto" />
              </button>
              <div className="flex items-center space-x-1.5 md:space-x-2">
                {user && <UserMenu />}
              </div>
            </div>
          </div>
        </div>

        {/* Topic Selection */}
        <div className="max-w-md mx-auto md:max-w-4xl px-2.5 md:px-4">
          <DebateTopicSelector onTopicSelected={handleTopicSelected} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Header with topic */}
      <div className="glass-panel-elevated sticky top-0 z-50 mx-2 md:mx-3 mt-1 md:mt-1.5 mb-2 md:mb-3 fade-in-up">
        <div className="max-w-md mx-auto md:max-w-4xl px-2.5 md:px-4 py-0.5 md:py-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <button onClick={handleBackToTopicSelection} className="hover:opacity-80 transition-opacity">
                <ArrowLeft className="w-5 h-5 text-content-primary" />
              </button>
              <button onClick={handleLogoClick} className="hover:opacity-80 transition-opacity">
                <SageLogo size="sm" className="md:w-auto" />
              </button>
              <div className="hidden md:block">
                <h1 className="text-sm font-medium text-content-primary truncate max-w-md">
                  {debateTopic}
                </h1>
              </div>
            </div>
            <div className="flex items-center space-x-1.5 md:space-x-2">
              {user && <UserMenu />}
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="glass-button p-1.5 hover:bg-white/60"
              >
                <Settings className="w-4 h-4 text-content-primary" />
              </button>
            </div>
          </div>
          
          {/* Mobile topic display */}
          <div className="md:hidden mt-2">
            <h1 className="text-sm font-medium text-content-primary">
              {debateTopic}
            </h1>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-md mx-auto md:max-w-4xl px-2.5 md:px-4 space-y-4">
        
                  {/* AI Moderators Control Panel */}
          <div className="glass-panel p-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-content-primary">AI Moderators</h2>
                {aiAgentsActive && (
                  <p className="text-sm text-content-secondary">
                    Moderating: <span className="font-medium text-blue-600">"{debateTopic}"</span>
                  </p>
                )}
              </div>
              <div className="flex gap-2 items-center">
                <Button 
                  onClick={launchAIAgents}
                  disabled={launchingAgents || aiAgentsActive}
                  variant={aiAgentsActive ? "secondary" : "default"}
                  size="sm"
                >
                  {launchingAgents ? "Launching..." : aiAgentsActive ? "🤖 Agents Active" : "🤖 Launch AI Moderators"}
                </Button>
                
                {aiAgentsActive && (
                  <Badge variant="secondary" className="bg-green-100 text-green-800">
                    5 AI Agents Active
                  </Badge>
                )}
              </div>
            </div>

          {/* AI Agent Status Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {aiAgents.map((agent) => (
              <div key={agent.name} className={`p-3 rounded-lg border-2 transition-all ${agent.status ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'}`}>
                <div className="text-center">
                  <div className="font-bold text-sm text-content-primary">{agent.name}</div>
                  <div className="text-xs text-content-secondary mb-2">{agent.role}</div>
                  <div className={`text-xs ${agent.status ? 'text-green-600' : 'text-gray-400'}`}>
                    {agent.status ? '🟢 Active' : '⚪ Inactive'}
                  </div>
                </div>
                <div className="mt-2 text-xs text-content-secondary leading-tight">
                  {agent.description}
                </div>
              </div>
            ))}
          </div>

          {/* Advanced AI Controls */}
          {aiAgentsActive && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
              <h3 className="font-bold mb-2 text-sm text-content-primary">AI Agent Controls</h3>
              <div className="flex gap-2">
                <Button 
                  variant="destructive" 
                  size="sm" 
                  onClick={stopAIAgents}
                  disabled={stoppingAgents}
                >
                  {stoppingAgents ? "Stopping..." : "Stop All AI Agents"}
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Main Audio Room */}
          <div className="lg:col-span-3">
            <div className="glass-panel p-4">
              <WebRTCAudioRoom 
                roomId={roomName} 
                debateTopic={debateTopic}
                onLeave={handleLeaveRoom}
                onAudioData={handleAudioData}
                onConnectionChange={handleWebRTCConnectionChange}
              />
            </div>
          </div>

          {/* AI Moderation Sidebar */}
          <div className="space-y-4">
            <div className="glass-panel p-4">
              <AIModerationPanel 
                roomId={roomName} 
                isWebRTCConnected={isWebRTCConnected}
                onAudioData={handleAIModerationReady}
              />
            </div>

            {/* Debate Rules Panel */}
            <div className="glass-panel p-4">
              <h3 className="text-sm font-semibold text-content-primary mb-3">
                Debate Rules
              </h3>
              <div className="space-y-2">
                <div className="text-xs text-content-secondary">
                  • No personal attacks
                </div>
                <div className="text-xs text-content-secondary">
                  • Provide sources for claims
                </div>
                <div className="text-xs text-content-secondary">
                  • Respect speaking turns
                </div>
                <div className="text-xs text-content-secondary">
                  • Stay on topic
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DebateRoom;

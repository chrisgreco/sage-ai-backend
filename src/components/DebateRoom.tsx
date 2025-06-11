
import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Settings } from 'lucide-react';
import SageLogo from './SageLogo';
import WebRTCAudioRoom from './WebRTCAudioRoom';
import AIModerationPanel from './AIModerationPanel';

const DebateRoom: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showSettings, setShowSettings] = useState(false);
  const [isWebRTCConnected, setIsWebRTCConnected] = useState(false);
  const [lastAudioTimestamp, setLastAudioTimestamp] = useState<number | null>(null);
  
  // Create a ref to store the AI moderation callback
  const aiModerationCallbackRef = useRef<((audioData: Float32Array) => void) | null>(null);

  const handleLeaveRoom = () => {
    navigate('/');
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="glass-panel-elevated sticky top-0 z-50 px-4 py-3 mb-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={handleLeaveRoom}
                className="glass-button p-2 hover:bg-white/60"
              >
                <ArrowLeft className="w-5 h-5 text-content-primary" />
              </button>
              <SageLogo size="sm" />
              <div>
                <h1 className="text-lg font-semibold text-content-primary">
                  Debate Room {id}
                </h1>
                <p className="text-sm text-content-secondary">
                  AI-Moderated Discussion
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="glass-button p-2 hover:bg-white/60"
            >
              <Settings className="w-5 h-5 text-content-primary" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Audio Room */}
          <div className="lg:col-span-3">
            <WebRTCAudioRoom 
              roomId={id || 'demo'} 
              onLeave={handleLeaveRoom}
              onAudioData={handleAudioData}
              onConnectionChange={handleWebRTCConnectionChange}
            />
          </div>

          {/* AI Moderation Sidebar */}
          <div className="space-y-4">
            <AIModerationPanel 
              roomId={id || 'demo'} 
              isWebRTCConnected={isWebRTCConnected}
              onAudioData={handleAIModerationReady}
            />

            {/* Debate Rules Panel */}
            <div className="glass-panel p-4">
              <h3 className="text-lg font-semibold text-content-primary mb-3">
                Debate Rules
              </h3>
              <div className="space-y-2">
                <div className="text-sm text-content-secondary">
                  • No personal attacks
                </div>
                <div className="text-sm text-content-secondary">
                  • Provide sources for claims
                </div>
                <div className="text-sm text-content-secondary">
                  • Respect speaking turns
                </div>
                <div className="text-sm text-content-secondary">
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

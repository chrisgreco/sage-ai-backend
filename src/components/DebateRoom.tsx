
import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Settings } from 'lucide-react';
import SageLogo from './SageLogo';
import WebRTCAudioRoom from './WebRTCAudioRoom';
import AIModerationPanel from './AIModerationPanel';
import UserMenu from './UserMenu';
import { useAuth } from '@/hooks/useAuth';

const DebateRoom: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [showSettings, setShowSettings] = useState(false);
  const [isWebRTCConnected, setIsWebRTCConnected] = useState(false);
  const [lastAudioTimestamp, setLastAudioTimestamp] = useState<number | null>(null);
  
  // Create a ref to store the AI moderation callback
  const aiModerationCallbackRef = useRef<((audioData: Float32Array) => void) | null>(null);

  const handleLeaveRoom = () => {
    navigate('/');
  };

  const handleLogoClick = () => {
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
    <div className="min-h-screen relative overflow-hidden">
      {/* Header matching homepage styling */}
      <div className="glass-panel-elevated sticky top-0 z-50 mx-2 md:mx-3 mt-1 md:mt-1.5 mb-2 md:mb-3 fade-in-up">
        <div className="max-w-md mx-auto md:max-w-4xl px-2.5 md:px-4 py-0.5 md:py-1">
          <div className="flex items-center justify-between">
            <button onClick={handleLogoClick} className="hover:opacity-80 transition-opacity">
              <SageLogo size="sm" className="md:w-auto" />
            </button>
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
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-md mx-auto md:max-w-6xl px-2.5 md:px-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Main Audio Room */}
          <div className="lg:col-span-3">
            <div className="glass-panel p-4" style={{
              background: 'linear-gradient(135deg, rgba(203, 213, 225, 0.08) 0%, rgba(255, 255, 255, 0.85) 30%, rgba(148, 163, 184, 0.06) 100%)',
              backdropFilter: 'blur(35px) saturate(2.2)',
              border: '1px solid rgba(255, 255, 255, 0.6)',
            }}>
              <WebRTCAudioRoom 
                roomId={id || 'demo'} 
                onLeave={handleLeaveRoom}
                onAudioData={handleAudioData}
                onConnectionChange={handleWebRTCConnectionChange}
              />
            </div>
          </div>

          {/* AI Moderation Sidebar */}
          <div className="space-y-4">
            <div className="glass-panel p-4" style={{
              background: 'linear-gradient(135deg, rgba(203, 213, 225, 0.08) 0%, rgba(255, 255, 255, 0.85) 30%, rgba(148, 163, 184, 0.06) 100%)',
              backdropFilter: 'blur(35px) saturate(2.2)',
              border: '1px solid rgba(255, 255, 255, 0.6)',
            }}>
              <AIModerationPanel 
                roomId={id || 'demo'} 
                isWebRTCConnected={isWebRTCConnected}
                onAudioData={handleAIModerationReady}
              />
            </div>

            {/* Debate Rules Panel */}
            <div className="glass-panel p-4" style={{
              background: 'linear-gradient(135deg, rgba(203, 213, 225, 0.08) 0%, rgba(255, 255, 255, 0.85) 30%, rgba(148, 163, 184, 0.06) 100%)',
              backdropFilter: 'blur(35px) saturate(2.2)',
              border: '1px solid rgba(255, 255, 255, 0.6)',
            }}>
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

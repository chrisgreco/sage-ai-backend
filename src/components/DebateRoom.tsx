
import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Settings } from 'lucide-react';
import SageLogo from './SageLogo';
import WebRTCAudioRoom from './WebRTCAudioRoom';

const DebateRoom: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showSettings, setShowSettings] = useState(false);

  const handleLeaveRoom = () => {
    navigate('/');
  };

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
      <div className="max-w-4xl mx-auto px-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Audio Room */}
          <div className="lg:col-span-2">
            <WebRTCAudioRoom 
              roomId={id || 'demo'} 
              onLeave={handleLeaveRoom}
            />
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* AI Moderators Panel */}
            <div className="glass-panel p-4">
              <h3 className="text-lg font-semibold text-content-primary mb-3">
                AI Moderators
              </h3>
              <div className="space-y-3">
                {[
                  { name: 'Socrates', role: 'Clarifier', active: true },
                  { name: 'Solon', role: 'Rule Enforcer', active: true },
                  { name: 'Buddha', role: 'Peacekeeper', active: true },
                  { name: 'Hermes', role: 'Summarizer', active: false },
                  { name: 'Aristotle', role: 'Fact-Checker', active: true }
                ].map((agent) => (
                  <div key={agent.name} className="agent-slot">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-content-primary">
                          {agent.name}
                        </p>
                        <p className="text-xs text-content-muted">{agent.role}</p>
                      </div>
                      <div className={`w-2 h-2 rounded-full ${
                        agent.active ? 'bg-green-500' : 'bg-gray-300'
                      }`} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

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

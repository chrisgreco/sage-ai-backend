
import React, { useState, useEffect } from 'react';
import { Play, Pause, Users, Clock, Settings } from 'lucide-react';
import SageLogo from './SageLogo';
import ParticipantSlot from './ParticipantSlot';

const DebateRoom: React.FC = () => {
  const [debateStarted, setDebateStarted] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [participants, setParticipants] = useState({
    speaker1: { connected: false, active: false, speaking: false, name: '' },
    speaker2: { connected: false, active: false, speaking: false, name: '' },
    audience: Array(3).fill({ connected: false, active: false }),
    agents: [
      { name: 'Socrates', active: true, speaking: false },
      { name: 'Aristotle', active: true, speaking: false },
      { name: 'Buddha', active: true, speaking: false }
    ]
  });

  const [currentTopic, setCurrentTopic] = useState('The Role of AI in Modern Society');

  const startDebate = () => {
    if (debateStarted) {
      setDebateStarted(false);
      setCountdown(0);
    } else {
      setCountdown(5);
      const timer = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(timer);
            setDebateStarted(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
  };

  const toggleParticipantMic = (type: 'speaker1' | 'speaker2') => {
    setParticipants(prev => ({
      ...prev,
      [type]: {
        ...prev[type],
        active: !prev[type].active,
        connected: true
      }
    }));
  };

  const toggleAudienceAudio = (index: number) => {
    setParticipants(prev => ({
      ...prev,
      audience: prev.audience.map((aud, i) => 
        i === index ? { ...aud, active: !aud.active, connected: true } : aud
      )
    }));
  };

  // Simulate speaking activity
  useEffect(() => {
    if (debateStarted) {
      const interval = setInterval(() => {
        const speakers = ['speaker1', 'speaker2'];
        const randomSpeaker = speakers[Math.floor(Math.random() * speakers.length)];
        
        setParticipants(prev => ({
          ...prev,
          [randomSpeaker]: {
            ...prev[randomSpeaker as keyof typeof prev],
            speaking: Math.random() > 0.7
          }
        }));
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [debateStarted]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="glass-panel-elevated p-6 mb-8 fade-in-up">
          <div className="flex items-center justify-between">
            <SageLogo size="lg" />
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <h1 className="text-2xl font-bold text-content-primary">Debate Room</h1>
                <p className="text-content-secondary">AI-Moderated Discussion Platform</p>
              </div>
              <button className="glass-button hover-lift">
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Current Topic */}
        <div className="glass-panel p-6 mb-8 scale-in">
          <div className="text-center">
            <h2 className="text-lg font-medium text-content-secondary mb-2">Current Debate Topic</h2>
            <h3 className="text-3xl font-bold text-gradient mb-4">{currentTopic}</h3>
            <div className="flex items-center justify-center space-x-4 text-content-muted">
              <div className="flex items-center space-x-2">
                <Users className="w-4 h-4" />
                <span>Live Discussion</span>
              </div>
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4" />
                <span>{debateStarted ? 'In Progress' : 'Ready to Start'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Participants */}
          <div className="lg:col-span-2 space-y-6">
            {/* Speaker Slots */}
            <div className="glass-panel p-6">
              <h3 className="text-xl font-semibold text-content-primary mb-4 flex items-center">
                <Users className="w-5 h-5 mr-2" />
                Debate Participants
              </h3>
              <div className="space-y-4">
                <ParticipantSlot
                  type="speaker"
                  isActive={participants.speaker1.active}
                  isSpeaking={participants.speaker1.speaking}
                  participantName="Speaker A"
                  isConnected={participants.speaker1.connected}
                  onToggleMic={() => toggleParticipantMic('speaker1')}
                />
                <ParticipantSlot
                  type="speaker"
                  isActive={participants.speaker2.active}
                  isSpeaking={participants.speaker2.speaking}
                  participantName="Speaker B"
                  isConnected={participants.speaker2.connected}
                  onToggleMic={() => toggleParticipantMic('speaker2')}
                />
              </div>
            </div>

            {/* Audience Slots */}
            <div className="glass-panel p-6">
              <h3 className="text-xl font-semibold text-content-primary mb-4 flex items-center">
                <Users className="w-5 h-5 mr-2" />
                Audience (Listen Only)
              </h3>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {participants.audience.map((audience, index) => (
                  <ParticipantSlot
                    key={index}
                    type="listener"
                    isActive={audience.active}
                    participantName={`Listener ${index + 1}`}
                    isConnected={audience.connected}
                    onToggleAudio={() => toggleAudienceAudio(index)}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Right Column - AI Agents & Controls */}
          <div className="space-y-6">
            {/* AI Moderators */}
            <div className="glass-panel p-6">
              <h3 className="text-xl font-semibold text-content-primary mb-4 flex items-center">
                <span className="w-5 h-5 mr-2 bg-gradient-to-r from-purple-500 to-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">AI</span>
                </span>
                AI Moderators
              </h3>
              <div className="space-y-3">
                {participants.agents.map((agent, index) => (
                  <ParticipantSlot
                    key={index}
                    type="agent"
                    isActive={agent.active}
                    isSpeaking={agent.speaking}
                    agentName={agent.name}
                    isConnected={true}
                  />
                ))}
              </div>
            </div>

            {/* Debate Controls */}
            <div className="glass-panel-elevated p-6">
              <h3 className="text-xl font-semibold text-content-primary mb-4">Debate Controls</h3>
              
              {countdown > 0 && (
                <div className="text-center mb-6">
                  <div className="text-4xl font-bold text-gradient mb-2">{countdown}</div>
                  <p className="text-content-secondary">Debate starting in...</p>
                </div>
              )}
              
              <button
                onClick={startDebate}
                className={`w-full glass-button text-lg py-4 flex items-center justify-center space-x-3 ${
                  debateStarted 
                    ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                    : 'bg-green-100 text-green-600 hover:bg-green-200'
                }`}
              >
                {debateStarted ? (
                  <>
                    <Pause className="w-6 h-6" />
                    <span>End Debate</span>
                  </>
                ) : (
                  <>
                    <Play className="w-6 h-6" />
                    <span>Start Debate</span>
                  </>
                )}
              </button>
              
              {debateStarted && (
                <div className="mt-4 text-center">
                  <div className="inline-flex items-center space-x-2 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span>Debate Live</span>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Stats */}
            <div className="glass-panel p-6">
              <h3 className="text-lg font-semibold text-content-primary mb-3">Session Stats</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-content-secondary">Active Speakers:</span>
                  <span className="font-medium text-content-primary">
                    {[participants.speaker1, participants.speaker2].filter(p => p.active).length}/2
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-content-secondary">Audience Connected:</span>
                  <span className="font-medium text-content-primary">
                    {participants.audience.filter(a => a.connected).length}/3
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-content-secondary">AI Agents:</span>
                  <span className="font-medium text-content-primary">
                    {participants.agents.filter(a => a.active).length}/3
                  </span>
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

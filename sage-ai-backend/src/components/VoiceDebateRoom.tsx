import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Room, 
  RoomEvent, 
  ConnectionState,
  LocalAudioTrack,
  RemoteAudioTrack,
  Participant,
  AudioTrack
} from 'livekit-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Mic, MicOff, Volume2, VolumeX, Users, MessageCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface VoiceDebateRoomProps {
  roomName: string;
  participantToken: string;
  onLeave: () => void;
}

interface AgentResponse {
  agent_name: string;
  agent_role: string;
  message: string;
  timestamp: number;
}

export function VoiceDebateRoom({ roomName, participantToken, onLeave }: VoiceDebateRoomProps) {
  // LiveKit state
  const [room, setRoom] = useState<Room | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  
  // Audio state
  const [isMuted, setIsMuted] = useState(false);
  const [isVolumeOn, setIsVolumeOn] = useState(true);
  const [audioLevel, setAudioLevel] = useState(0);
  
  // Conversation state
  const [isListening, setIsListening] = useState(false);
  const [lastTranscript, setLastTranscript] = useState('');
  const [agentResponses, setAgentResponses] = useState<AgentResponse[]>([]);
  const [currentSpeaker, setCurrentSpeaker] = useState<string | null>(null);
  
  // Participants
  const [participants, setParticipants] = useState<Participant[]>([]);
  
  const { toast } = useToast();
  const audioContextRef = useRef<AudioContext | null>(null);
  const localAudioTrackRef = useRef<LocalAudioTrack | null>(null);

  // Initialize LiveKit connection
  const connectToRoom = useCallback(async () => {
    if (isConnecting || isConnected) return;
    
    setIsConnecting(true);
    
    try {
      const newRoom = new Room({
        adaptiveStream: true,
        dynacast: true,
        audioCaptureDefaults: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // Room event handlers
      newRoom.on(RoomEvent.Connected, () => {
        console.log('Connected to LiveKit room:', roomName);
        setIsConnected(true);
        setIsConnecting(false);
        
        toast({
          title: "Connected to Voice Debate",
          description: `Joined room: ${roomName}`,
        });
      });

      newRoom.on(RoomEvent.Disconnected, () => {
        console.log('Disconnected from room');
        setIsConnected(false);
        setRoom(null);
      });

      newRoom.on(RoomEvent.ParticipantConnected, (participant) => {
        console.log('Participant connected:', participant.identity);
        setParticipants(prev => [...prev, participant]);
        
        if (participant.identity.includes('sage-ai-assistant')) {
          toast({
            title: "AI Agent Joined",
            description: "Sage AI agents are now active in the conversation",
          });
        }
      });

      newRoom.on(RoomEvent.ParticipantDisconnected, (participant) => {
        console.log('Participant disconnected:', participant.identity);
        setParticipants(prev => prev.filter(p => p.sid !== participant.sid));
      });

      newRoom.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        if (track instanceof RemoteAudioTrack) {
          console.log('Audio track subscribed from:', participant.identity);
          
          // Play audio from AI agents
          if (participant.identity.includes('sage-ai-assistant')) {
            track.attach();
            setCurrentSpeaker(participant.identity);
            
            // Clear current speaker after a delay
            setTimeout(() => setCurrentSpeaker(null), 3000);
          }
        }
      });

      newRoom.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
        if (track instanceof RemoteAudioTrack) {
          track.detach();
        }
      });

      // Connect to the room
      const wsUrl = process.env.NODE_ENV === 'development' 
        ? 'ws://localhost:7880'  // Local LiveKit server
        : 'wss://sage-ai-backend-l0en.onrender.com';  // Production

      await newRoom.connect(wsUrl, participantToken);
      setRoom(newRoom);

      // Enable microphone by default
      await enableMicrophone(newRoom);
      
    } catch (error) {
      console.error('Failed to connect to room:', error);
      setIsConnecting(false);
      
      toast({
        title: "Connection Failed",
        description: "Could not connect to the voice debate room",
        variant: "destructive",
      });
    }
  }, [isConnecting, isConnected, roomName, participantToken, toast]);

  // Enable microphone
  const enableMicrophone = async (roomInstance: Room = room!) => {
    try {
      const track = await LocalAudioTrack.createAudioTrack({
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      });

      await roomInstance.localParticipant.publishTrack(track);
      localAudioTrackRef.current = track;
      
      // Set up audio level monitoring
      setupAudioLevelMonitoring(track);
      
      setIsMuted(false);
      setIsListening(true);
      
    } catch (error) {
      console.error('Failed to enable microphone:', error);
      toast({
        title: "Microphone Error",
        description: "Could not access your microphone",
        variant: "destructive",
      });
    }
  };

  // Audio level monitoring for visual feedback
  const setupAudioLevelMonitoring = (track: LocalAudioTrack) => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
    }

    const mediaStream = new MediaStream([track.mediaStreamTrack]);
    const source = audioContextRef.current.createMediaStreamSource(mediaStream);
    const analyser = audioContextRef.current.createAnalyser();
    
    analyser.fftSize = 256;
    source.connect(analyser);
    
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    
    const updateAudioLevel = () => {
      if (!isConnected) return;
      
      analyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setAudioLevel(average / 255);
      
      requestAnimationFrame(updateAudioLevel);
    };
    
    updateAudioLevel();
  };

  // Toggle microphone mute
  const toggleMute = async () => {
    if (!room || !localAudioTrackRef.current) return;
    
    if (isMuted) {
      localAudioTrackRef.current.unmute();
      setIsListening(true);
    } else {
      localAudioTrackRef.current.mute();
      setIsListening(false);
    }
    
    setIsMuted(!isMuted);
  };

  // Toggle volume
  const toggleVolume = () => {
    setIsVolumeOn(!isVolumeOn);
    
    // Mute/unmute all remote audio tracks
    if (room) {
      room.participants.forEach(participant => {
        participant.audioTracks.forEach(publication => {
          if (publication.track instanceof RemoteAudioTrack) {
            if (isVolumeOn) {
              publication.track.setVolume(0);
            } else {
              publication.track.setVolume(1);
            }
          }
        });
      });
    }
  };

  // Leave room
  const leaveRoom = async () => {
    if (room) {
      await room.disconnect();
    }
    
    if (localAudioTrackRef.current) {
      localAudioTrackRef.current.stop();
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
    
    onLeave();
  };

  // Connect on mount
  useEffect(() => {
    connectToRoom();
    
    return () => {
      // Cleanup on unmount
      if (room) {
        room.disconnect();
      }
    };
  }, [connectToRoom]);

  // Mock agent response simulation (replace with real WebSocket/API integration)
  useEffect(() => {
    if (isListening && lastTranscript) {
      const timer = setTimeout(() => {
        const mockResponse: AgentResponse = {
          agent_name: "Aristotle",
          agent_role: "Fact-Checker", 
          message: `I understand you said: "${lastTranscript}". Let me provide some context...`,
          timestamp: Date.now()
        };
        
        setAgentResponses(prev => [...prev, mockResponse]);
      }, 2000);
      
      return () => clearTimeout(timer);
    }
  }, [lastTranscript, isListening]);

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-purple-50 to-blue-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b p-4">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Voice Debate Room</h1>
            <p className="text-gray-600">{roomName}</p>
          </div>
          
          <div className="flex items-center gap-4">
            <Badge variant={isConnected ? "default" : "secondary"}>
              {isConnected ? "Connected" : isConnecting ? "Connecting..." : "Disconnected"}
            </Badge>
            
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Users className="w-4 h-4" />
              {participants.length + 1} participants
            </div>
            
            <Button variant="outline" onClick={leaveRoom}>
              Leave Room
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-6 p-6 max-w-6xl mx-auto w-full">
        
        {/* Voice Controls */}
        <Card className="w-80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mic className="w-5 h-5" />
              Voice Controls
            </CardTitle>
            <CardDescription>
              Manage your microphone and audio settings
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-4">
            {/* Microphone Control */}
            <div className="flex items-center gap-3">
              <Button
                onClick={toggleMute}
                variant={isMuted ? "destructive" : "default"}
                size="lg"
                className="flex-1"
                disabled={!isConnected}
              >
                {isMuted ? <MicOff className="w-5 h-5 mr-2" /> : <Mic className="w-5 h-5 mr-2" />}
                {isMuted ? "Unmute" : "Mute"}
              </Button>
              
              <Button
                onClick={toggleVolume}
                variant={isVolumeOn ? "default" : "secondary"}
                size="lg"
              >
                {isVolumeOn ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
              </Button>
            </div>

            {/* Audio Level Indicator */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Audio Level</label>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-green-500 h-3 rounded-full transition-all duration-150"
                  style={{ width: `${audioLevel * 100}%` }}
                />
              </div>
            </div>

            {/* Status Indicators */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Listening:</span>
                <Badge variant={isListening ? "default" : "secondary"}>
                  {isListening ? "Active" : "Inactive"}
                </Badge>
              </div>
              
              {currentSpeaker && (
                <div className="flex items-center justify-between text-sm">
                  <span>Speaking:</span>
                  <Badge variant="outline">{currentSpeaker}</Badge>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Conversation Feed */}
        <Card className="flex-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageCircle className="w-5 h-5" />
              Live Conversation
            </CardTitle>
            <CardDescription>
              Real-time voice conversation with Sage AI agents
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              
              {/* Last Transcript */}
              {lastTranscript && (
                <div className="bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">
                  <div className="text-sm font-medium text-blue-800">You said:</div>
                  <div className="text-blue-700">{lastTranscript}</div>
                </div>
              )}
              
              {/* Agent Responses */}
              {agentResponses.map((response, index) => (
                <div key={index} className="bg-purple-50 p-3 rounded-lg border-l-4 border-purple-400">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="text-sm font-medium text-purple-800">
                      {response.agent_name}
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {response.agent_role}
                    </Badge>
                  </div>
                  <div className="text-purple-700">{response.message}</div>
                </div>
              ))}
              
              {/* Connection Status */}
              {!isConnected && (
                <div className="text-center py-8 text-gray-500">
                  {isConnecting ? "Connecting to voice room..." : "Not connected to voice room"}
                </div>
              )}
              
              {isConnected && agentResponses.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  Start speaking to begin your debate with the Sage AI agents
                </div>
              )}
              
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 

import React from 'react';
import { Users } from 'lucide-react';

interface DebateRoom {
  id: number;
  title: string;
  topic: string;
  participants: number;
  isLive: boolean;
  category: string;
  gradient: string;
}

interface DebateStoryCircleProps {
  room: DebateRoom;
}

const DebateStoryCircle: React.FC<DebateStoryCircleProps> = ({ room }) => {
  return (
    <div className="flex-shrink-0 cursor-pointer group">
      <div className="relative">
        {/* Enhanced Story Circle with organic glass effect and flowing animations */}
        <div className={`relative w-20 h-20 bg-gradient-to-br ${room.gradient} p-1 shadow-2xl ${room.isLive ? 'animate-pulse-glow shadow-green-400/30' : 'shadow-black/10'} story-circle liquid-morph`}>
          <div className="w-full h-full backdrop-blur-lg flex items-center justify-center border-2 border-white/60 group-hover:scale-105 transition-all duration-500 shadow-inner icon-container liquid-morph"
               style={{ 
                 background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.7) 100%)',
               }}>
            <div className="text-center">
              <div className="text-xs font-bold text-slate-800 leading-tight tracking-wide">
                {room.title.split(' ').map(word => word.slice(0, 2)).join('')}
              </div>
            </div>
          </div>
          
          {/* Enhanced Live indicator with organic shape and flowing animation */}
          {room.isLive && (
            <div className="absolute -bottom-1 -right-1 w-7 h-7 bg-gradient-to-br from-green-400 to-emerald-500 border-3 border-white flex items-center justify-center shadow-lg shadow-green-500/30 organic-pulse liquid-morph">
              <div className="w-2.5 h-2.5 bg-white animate-pulse organic-pulse"></div>
            </div>
          )}
        </div>

        {/* Enhanced tooltip with organic glass morphism */}
        <div className="absolute top-24 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-all duration-500 z-20 group-hover:translate-y-1">
          <div className="glass-panel-elevated px-4 py-3 whitespace-nowrap shadow-2xl shadow-black/15 min-w-max liquid-morph">
            <div className="font-semibold text-slate-800 text-sm">{room.topic}</div>
            <div className="flex items-center mt-2 text-xs text-slate-600">
              <Users className="w-3 h-3 mr-1.5" />
              <span>{room.participants} joined</span>
              {room.isLive && (
                <>
                  <div className="w-1 h-1 bg-green-500 mx-2 animate-pulse organic-pulse"></div>
                  <span className="text-green-600 font-medium">Live</span>
                </>
              )}
            </div>
            {/* Enhanced arrow with organic curve */}
            <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-b-4 border-transparent border-b-white/80"
                 style={{ filter: 'drop-shadow(0 -1px 2px rgba(0,0,0,0.1))' }}></div>
          </div>
        </div>
      </div>

      {/* Enhanced title with better typography */}
      <div className="mt-3 text-center">
        <div className="text-sm font-semibold text-slate-700 truncate w-20">
          {room.title}
        </div>
      </div>
    </div>
  );
};

export default DebateStoryCircle;

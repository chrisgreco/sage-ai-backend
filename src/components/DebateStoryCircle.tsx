
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
        {/* Story Circle */}
        <div className={`relative w-20 h-20 rounded-full bg-gradient-to-br ${room.gradient} p-0.5 ${room.isLive ? 'animate-pulse-glow' : ''}`}>
          <div className="w-full h-full rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center">
            <div className="text-center">
              <div className="text-xs font-bold text-slate-800 leading-tight">
                {room.title.split(' ').map(word => word.slice(0, 2)).join('')}
              </div>
            </div>
          </div>
          
          {/* Live indicator */}
          {room.isLive && (
            <div className="absolute -top-1 -right-1 w-6 h-6 bg-green-500 rounded-full border-2 border-white flex items-center justify-center">
              <div className="w-2 h-2 bg-white rounded-full"></div>
            </div>
          )}
        </div>

        {/* Tooltip on hover */}
        <div className="absolute top-24 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
          <div className="bg-slate-800 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg">
            <div className="font-semibold">{room.topic}</div>
            <div className="flex items-center mt-1 text-slate-300">
              <Users className="w-3 h-3 mr-1" />
              <span>{room.participants} joined</span>
            </div>
            {/* Arrow */}
            <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-slate-800 rotate-45"></div>
          </div>
        </div>
      </div>

      {/* Title below */}
      <div className="mt-2 text-center">
        <div className="text-xs font-medium text-slate-700 truncate w-20">
          {room.title}
        </div>
      </div>
    </div>
  );
};

export default DebateStoryCircle;

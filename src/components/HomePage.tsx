import React, { useState } from 'react';
import { Play, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import SageLogo from './SageLogo';
import UserMenu from './UserMenu';
import DebateStoryCircle from './DebateStoryCircle';

const HomePage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [featuredRooms] = useState([
    {
      id: 1,
      title: 'AI Ethics',
      topic: 'Should AI have rights?',
      participants: 47,
      isLive: true,
      category: 'Technology',
      gradient: 'from-silver-500 to-silver-600'
    },
    {
      id: 2,
      title: 'Climate Action',
      topic: 'Nuclear vs Renewable Energy',
      participants: 23,
      isLive: true,
      category: 'Environment',
      gradient: 'from-silver-400 to-silver-500'
    },
    {
      id: 3,
      title: 'Philosophy',
      topic: 'Free Will vs Determinism',
      participants: 15,
      isLive: false,
      category: 'Philosophy',
      gradient: 'from-silver-500 to-silver-600'
    },
    {
      id: 4,
      title: 'Economics',
      topic: 'Universal Basic Income',
      participants: 31,
      isLive: true,
      category: 'Economics',
      gradient: 'from-silver-400 to-silver-600'
    },
    {
      id: 5,
      title: 'Politics',
      topic: 'Democracy in Digital Age',
      participants: 8,
      isLive: false,
      category: 'Politics',
      gradient: 'from-silver-500 to-silver-700'
    },
    {
      id: 6,
      title: 'Science',
      topic: 'Space Exploration Priority',
      participants: 19,
      isLive: true,
      category: 'Science',
      gradient: 'from-silver-400 to-silver-500'
    }
  ]);

  const handleStartDebate = () => {
    navigate('/debate/demo');
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Thinner, sleeker header with smaller font sizes */}
      <div className="glass-panel-elevated sticky top-0 z-50 mx-2 md:mx-3 mt-1.5 md:mt-2 mb-2 md:mb-3 fade-in-up">
        <div className="max-w-md mx-auto md:max-w-4xl px-2.5 md:px-4 py-1 md:py-1.5">
          <div className="flex items-center justify-between">
            <SageLogo size="sm" className="md:w-auto" />
            <div className="flex items-center space-x-1.5 md:space-x-2">
              {user && <UserMenu />}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Container */}
      <div className="max-w-md mx-auto md:max-w-4xl px-2.5">
        
        {/* Stories Section - Only Live Debates have flowing effect */}
        <div className="mb-4">
          <div className="relative mb-2.5">
            <div className="glass-panel p-2.5 liquid-morph" style={{
              background: 'linear-gradient(135deg, rgba(203, 213, 225, 0.08) 0%, rgba(255, 255, 255, 0.85) 30%, rgba(148, 163, 184, 0.06) 100%)',
              backdropFilter: 'blur(35px) saturate(2.2)',
              border: '1px solid rgba(255, 255, 255, 0.6)',
            }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="relative">
                    <div className="w-7 h-7 bg-gradient-to-br from-liquid-400 to-liquid-600 shadow-lg shadow-liquid-500/25 icon-container">
                      <div className="w-full h-full backdrop-blur-sm flex items-center justify-center border-2 border-white/60 icon-container"
                           style={{ 
                             background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.7) 100%)',
                           }}>
                        <div className="w-1.5 h-1.5 bg-gradient-to-r from-green-400 to-emerald-500 animate-pulse shadow-lg shadow-green-400/30 organic-pulse"></div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-liquid-800">Live Debates</h2>
                    <p className="text-xs text-liquid-600 font-medium">Real-time AI moderated discussions</p>
                  </div>
                </div>
                <div className="glass-panel px-2 py-0.5" style={{
                  background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.12) 0%, rgba(255, 255, 255, 0.8) 100%)',
                  border: '1px solid rgba(34, 197, 94, 0.3)',
                }}>
                  <div className="flex items-center space-x-1 text-xs">
                    <div className="w-1 h-1 bg-gradient-to-r from-green-400 to-emerald-500 animate-pulse shadow-lg shadow-green-400/30 organic-pulse"></div>
                    <span className="font-medium text-green-700">{featuredRooms.filter(room => room.isLive).length} live now</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex space-x-2.5 overflow-x-auto pb-2.5 scrollbar-hide px-1.5">
            {/* Start Debate Story */}
            <div className="flex-shrink-0 cursor-pointer group" onClick={handleStartDebate}>
              <div className="relative story-circle">
                <div className="w-12 h-12 bg-gradient-to-br from-liquid-500 via-liquid-600 to-liquid-700 p-0.5 shadow-xl shadow-liquid-500/25 icon-container">
                  <div className="w-full h-full backdrop-blur-sm flex items-center justify-center border-2 border-white/50 group-hover:scale-105 transition-all duration-500 icon-container"
                       style={{ 
                         background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.8) 100%)',
                       }}>
                    <Play className="w-3.5 h-3.5 text-liquid-800 group-hover:text-liquid-600 transition-colors duration-300" />
                  </div>
                </div>
              </div>
              <div className="mt-1 text-center">
                <div className="text-xs font-medium text-content-primary truncate w-12">
                  Start
                </div>
              </div>
            </div>

            {/* Debate Room Stories */}
            {featuredRooms.map((room) => (
              <DebateStoryCircle key={room.id} room={room} />
            ))}
          </div>
        </div>

        {/* Main Feed Area */}
        <div className="space-y-4">
          {/* Hero Section with enhanced blur effect */}
          <div className="glass-panel p-4 text-center scale-in" style={{
            background: 'linear-gradient(135deg, rgba(203, 213, 225, 0.08) 0%, rgba(255, 255, 255, 0.85) 30%, rgba(148, 163, 184, 0.06) 100%)',
            backdropFilter: 'blur(35px) saturate(2.2)',
            border: '1px solid rgba(255, 255, 255, 0.6)',
          }}>
            <div className="relative">
              <h1 className="text-xl md:text-2xl font-semibold mb-2 leading-tight"
                  style={{
                    background: 'linear-gradient(135deg, #475569 0%, #64748b 50%, #94a3b8 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text'
                  }}>
                Civil Discourse, Powered by AI
              </h1>
              <p className="text-sm text-liquid-700 mb-4 max-w-xl mx-auto leading-relaxed font-medium">
                Join thoughtful debates moderated by ancient wisdom. 
                Socrates, Aristotle, and Buddha guide meaningful conversations.
              </p>

              <button 
                onClick={handleStartDebate}
                className="glass-button text-sm px-4 py-2 bg-gradient-to-r from-liquid-500 via-liquid-600 to-liquid-700 text-white hover:shadow-xl hover:shadow-liquid-500/25 transition-all duration-500 hover:scale-105 w-full md:w-auto font-medium"
                style={{ borderRadius: '16px 12px 18px 10px' }}
              >
                <div className="flex items-center justify-center space-x-1.5">
                  <Play className="w-3 h-3" />
                  <span>Start a Debate</span>
                </div>
              </button>
            </div>
          </div>

          {/* Categories Grid with enhanced blur effect */}
          <div className="glass-panel p-4" style={{
            background: 'linear-gradient(135deg, rgba(203, 213, 225, 0.08) 0%, rgba(255, 255, 255, 0.85) 30%, rgba(148, 163, 184, 0.06) 100%)',
            backdropFilter: 'blur(35px) saturate(2.2)',
            border: '1px solid rgba(255, 255, 255, 0.6)',
          }}>
            <h2 className="text-sm font-semibold text-liquid-800 mb-2.5">Explore Topics</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {['Philosophy', 'Technology', 'Politics', 'Science', 'Ethics', 'Economics'].map((category) => (
                <div key={category} className="group cursor-pointer">
                  <div className="glass-panel p-2.5 hover:bg-white/85 transition-all duration-500 hover:scale-105 hover:shadow-lg hover:shadow-black/10">
                    <h3 className="font-medium text-liquid-800 mb-0.5 text-xs">{category}</h3>
                    <div className="flex items-center text-xs text-liquid-600">
                      <Users className="w-2 h-2 mr-0.5" />
                      <span>{Math.floor(Math.random() * 50) + 10} debates</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;

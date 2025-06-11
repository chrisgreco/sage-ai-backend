
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
      {/* Header */}
      <div className="glass-panel-elevated sticky top-0 z-50 mx-3 md:mx-4 mt-2 md:mt-3 mb-3 md:mb-4 fade-in-up liquid-morph">
        <div className="max-w-md mx-auto md:max-w-4xl px-3 md:px-5 py-2 md:py-2.5">
          <div className="flex items-center justify-between">
            <SageLogo size="sm" className="md:w-auto" />
            <div className="flex items-center space-x-2 md:space-x-3">
              {user && <UserMenu />}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Container */}
      <div className="max-w-md mx-auto md:max-w-4xl px-3">
        
        {/* Stories Section */}
        <div className="mb-5">
          <div className="relative mb-3">
            <div className="glass-panel p-3 liquid-morph" style={{
              background: 'linear-gradient(135deg, rgba(203, 213, 225, 0.06) 0%, rgba(255, 255, 255, 0.8) 30%, rgba(148, 163, 184, 0.04) 100%)',
              backdropFilter: 'blur(25px) saturate(1.8)',
              border: '1px solid rgba(255, 255, 255, 0.5)',
            }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className="relative">
                    <div className="w-8 h-8 bg-gradient-to-br from-silver-400 to-silver-600 shadow-lg shadow-silver-500/20 icon-container">
                      <div className="w-full h-full backdrop-blur-sm flex items-center justify-center border-2 border-white/50 icon-container"
                           style={{ 
                             background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.85) 0%, rgba(255, 255, 255, 0.65) 100%)',
                           }}>
                        <div className="w-2 h-2 bg-gradient-to-r from-green-400 to-emerald-500 animate-pulse shadow-lg shadow-green-400/25 organic-pulse"></div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-silver-800">Live Debates</h2>
                    <p className="text-xs text-silver-600 font-medium">Real-time AI moderated discussions</p>
                  </div>
                </div>
                <div className="glass-panel px-2.5 py-1 liquid-morph" style={{
                  background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(255, 255, 255, 0.75) 100%)',
                  border: '1px solid rgba(34, 197, 94, 0.25)',
                }}>
                  <div className="flex items-center space-x-1 text-xs">
                    <div className="w-1 h-1 bg-gradient-to-r from-green-400 to-emerald-500 animate-pulse shadow-lg shadow-green-400/25 organic-pulse"></div>
                    <span className="font-medium text-green-700">{featuredRooms.filter(room => room.isLive).length} live now</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex space-x-3 overflow-x-auto pb-3 scrollbar-hide px-2">
            {/* Start Debate Story */}
            <div className="flex-shrink-0 cursor-pointer group" onClick={handleStartDebate}>
              <div className="relative story-circle">
                <div className="w-14 h-14 bg-gradient-to-br from-silver-500 via-silver-600 to-silver-700 p-1 shadow-xl shadow-silver-500/20 icon-container liquid-morph">
                  <div className="w-full h-full backdrop-blur-sm flex items-center justify-center border-2 border-white/40 group-hover:scale-105 transition-all duration-500 icon-container liquid-morph"
                       style={{ 
                         background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.8) 100%)',
                       }}>
                    <Play className="w-4 h-4 text-silver-800 group-hover:text-silver-600 transition-colors duration-300" />
                  </div>
                </div>
              </div>
              <div className="mt-1.5 text-center">
                <div className="text-xs font-medium text-content-primary truncate w-14">
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
        <div className="space-y-5">
          {/* Hero Section */}
          <div className="glass-panel p-5 text-center scale-in liquid-morph">
            <div className="relative">
              <h1 className="text-2xl md:text-3xl font-semibold mb-2.5 leading-tight"
                  style={{
                    background: 'linear-gradient(135deg, #475569 0%, #64748b 50%, #94a3b8 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text'
                  }}>
                Civil Discourse, Powered by AI
              </h1>
              <p className="text-sm text-silver-700 mb-5 max-w-xl mx-auto leading-relaxed font-medium">
                Join thoughtful debates moderated by ancient wisdom. 
                Socrates, Aristotle, and Buddha guide meaningful conversations.
              </p>

              <button 
                onClick={handleStartDebate}
                className="glass-button text-sm px-5 py-2.5 bg-gradient-to-r from-silver-500 via-silver-600 to-silver-700 text-white hover:shadow-xl hover:shadow-silver-500/20 transition-all duration-500 hover:scale-105 w-full md:w-auto font-medium"
                style={{ borderRadius: '18px 14px 20px 12px' }}
              >
                <div className="flex items-center justify-center space-x-2">
                  <Play className="w-3.5 h-3.5" />
                  <span>Start a Debate</span>
                </div>
              </button>
            </div>
          </div>

          {/* Categories Grid */}
          <div className="glass-panel p-5 liquid-morph">
            <h2 className="text-base font-semibold text-silver-800 mb-3">Explore Topics</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
              {['Philosophy', 'Technology', 'Politics', 'Science', 'Ethics', 'Economics'].map((category) => (
                <div key={category} className="group cursor-pointer">
                  <div className="glass-panel p-3 hover:bg-white/75 transition-all duration-500 hover:scale-105 hover:shadow-lg hover:shadow-black/8 liquid-morph">
                    <h3 className="font-medium text-silver-800 mb-1 text-xs">{category}</h3>
                    <div className="flex items-center text-xs text-silver-600">
                      <Users className="w-2.5 h-2.5 mr-1" />
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

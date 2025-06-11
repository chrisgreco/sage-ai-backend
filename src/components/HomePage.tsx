
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
      gradient: 'from-slate-500 to-gray-600'
    },
    {
      id: 2,
      title: 'Climate Action',
      topic: 'Nuclear vs Renewable Energy',
      participants: 23,
      isLive: true,
      category: 'Environment',
      gradient: 'from-gray-500 to-slate-600'
    },
    {
      id: 3,
      title: 'Philosophy',
      topic: 'Free Will vs Determinism',
      participants: 15,
      isLive: false,
      category: 'Philosophy',
      gradient: 'from-zinc-500 to-gray-600'
    },
    {
      id: 4,
      title: 'Economics',
      topic: 'Universal Basic Income',
      participants: 31,
      isLive: true,
      category: 'Economics',
      gradient: 'from-neutral-500 to-slate-600'
    },
    {
      id: 5,
      title: 'Politics',
      topic: 'Democracy in Digital Age',
      participants: 8,
      isLive: false,
      category: 'Politics',
      gradient: 'from-gray-500 to-zinc-600'
    },
    {
      id: 6,
      title: 'Science',
      topic: 'Space Exploration Priority',
      participants: 19,
      isLive: true,
      category: 'Science',
      gradient: 'from-slate-500 to-neutral-600'
    }
  ]);

  const handleStartDebate = () => {
    navigate('/debate/demo');
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Enhanced Background with silver floating elements */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50/90 via-white/80 to-gray-50/90"></div>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-gradient-to-r from-slate-400/20 to-gray-400/20 blur-3xl floating-element"></div>
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-gradient-to-r from-zinc-400/20 to-neutral-400/20 blur-3xl floating-element" style={{ animationDelay: '-3s' }}></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-72 h-72 bg-gradient-to-r from-gray-400/15 to-slate-400/15 blur-3xl floating-element" style={{ animationDelay: '-1.5s' }}></div>
      </div>

      {/* Enhanced iOS-style Header with improved mobile spacing */}
      <div className="glass-panel-elevated sticky top-0 z-50 mx-3 md:mx-4 mt-2 md:mt-4 mb-4 md:mb-6 fade-in-up liquid-morph">
        <div className="max-w-md mx-auto md:max-w-4xl px-4 md:px-6 py-3 md:py-4">
          <div className="flex items-center justify-between">
            <SageLogo size="sm" className="md:w-auto" />
            <div className="flex items-center space-x-2 md:space-x-3">
              {user && <UserMenu />}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Container */}
      <div className="max-w-md mx-auto md:max-w-4xl px-4">
        
        {/* Enhanced Stories Section with silver aesthetic */}
        <div className="mb-8">
          {/* Silver-themed header container */}
          <div className="relative mb-6">
            <div className="glass-panel p-6 liquid-morph" style={{
              background: 'linear-gradient(135deg, rgba(148, 163, 184, 0.08) 0%, rgba(255, 255, 255, 0.85) 30%, rgba(100, 116, 139, 0.06) 100%)',
              backdropFilter: 'blur(20px) saturate(1.8)',
              border: '1px solid rgba(255, 255, 255, 0.6)',
            }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="relative">
                    <div className="w-12 h-12 bg-gradient-to-br from-slate-500 to-gray-600 shadow-lg shadow-slate-500/25 icon-container">
                      <div className="w-full h-full backdrop-blur-sm flex items-center justify-center border-2 border-white/60 icon-container"
                           style={{ 
                             background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.7) 100%)',
                           }}>
                        <div className="w-3 h-3 bg-gradient-to-r from-green-400 to-emerald-500 animate-pulse shadow-lg shadow-green-400/30 organic-pulse"></div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-800">Live Debates</h2>
                    <p className="text-sm text-slate-600 font-medium">Real-time AI moderated discussions</p>
                  </div>
                </div>
                <div className="glass-panel px-4 py-2 liquid-morph" style={{
                  background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.12) 0%, rgba(255, 255, 255, 0.8) 100%)',
                  border: '1px solid rgba(34, 197, 94, 0.3)',
                }}>
                  <div className="flex items-center space-x-2 text-sm">
                    <div className="w-2 h-2 bg-gradient-to-r from-green-400 to-emerald-500 animate-pulse shadow-lg shadow-green-400/30 organic-pulse"></div>
                    <span className="font-semibold text-green-700">{featuredRooms.filter(room => room.isLive).length} live now</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex space-x-6 overflow-x-auto pb-6 scrollbar-hide px-3">
            {/* Enhanced Start Debate Story with silver theme */}
            <div className="flex-shrink-0 cursor-pointer group" onClick={handleStartDebate}>
              <div className="relative story-circle">
                <div className="w-20 h-20 bg-gradient-to-br from-slate-600 via-gray-600 to-zinc-700 p-1 shadow-2xl shadow-slate-500/25 icon-container liquid-morph">
                  <div className="w-full h-full backdrop-blur-sm flex items-center justify-center border-2 border-white/50 group-hover:scale-105 transition-all duration-500 icon-container liquid-morph"
                       style={{ 
                         background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.85) 100%)',
                       }}>
                    <Play className="w-7 h-7 text-slate-800 group-hover:text-slate-600 transition-colors duration-300" />
                  </div>
                </div>
              </div>
              <div className="mt-3 text-center">
                <div className="text-sm font-semibold text-content-primary truncate w-20">
                  Start
                </div>
              </div>
            </div>

            {/* Enhanced Debate Room Stories with flowing animations */}
            {featuredRooms.map((room) => (
              <DebateStoryCircle key={room.id} room={room} />
            ))}
          </div>
        </div>

        {/* Enhanced Main Feed Area with silver theme */}
        <div className="space-y-8">
          {/* Enhanced Hero Section with silver aesthetic and better text contrast */}
          <div className="glass-panel p-8 text-center scale-in liquid-morph">
            <div className="relative">
              <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-tight"
                  style={{
                    background: 'linear-gradient(135deg, #475569 0%, #64748b 50%, #334155 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text'
                  }}>
                Civil Discourse, Powered by AI
              </h1>
              <p className="text-lg text-slate-700 mb-8 max-w-xl mx-auto leading-relaxed font-medium">
                Join thoughtful debates moderated by ancient wisdom. 
                Socrates, Aristotle, and Buddha guide meaningful conversations.
              </p>

              <button 
                onClick={handleStartDebate}
                className="glass-button text-lg px-8 py-4 bg-gradient-to-r from-slate-600 via-gray-600 to-zinc-600 text-white hover:shadow-2xl hover:shadow-slate-500/25 transition-all duration-500 hover:scale-105 w-full md:w-auto font-semibold"
                style={{ borderRadius: '28px 20px 32px 18px' }}
              >
                <div className="flex items-center justify-center space-x-3">
                  <Play className="w-5 h-5" />
                  <span>Start a Debate</span>
                </div>
              </button>
            </div>
          </div>

          {/* Enhanced Categories Grid with silver aesthetic */}
          <div className="glass-panel p-8 liquid-morph">
            <h2 className="text-xl font-semibold text-slate-800 mb-6">Explore Topics</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {['Philosophy', 'Technology', 'Politics', 'Science', 'Ethics', 'Economics'].map((category) => (
                <div key={category} className="group cursor-pointer">
                  <div className="glass-panel p-6 hover:bg-white/80 transition-all duration-500 hover:scale-105 hover:shadow-xl hover:shadow-black/10 liquid-morph">
                    <h3 className="font-semibold text-slate-800 mb-2 text-base">{category}</h3>
                    <div className="flex items-center text-sm text-slate-600">
                      <Users className="w-4 h-4 mr-2" />
                      <span>{Math.floor(Math.random() * 50) + 10} debates</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Floating ambient particles with silver aesthetic */}
      <div className="fixed inset-0 pointer-events-none -z-5">
        <div className="absolute top-1/3 left-1/6 w-2 h-2 bg-slate-400/30 animate-pulse organic-pulse" style={{ animationDelay: '0s' }}></div>
        <div className="absolute top-2/3 right-1/4 w-1.5 h-1.5 bg-gray-400/30 animate-pulse organic-pulse" style={{ animationDelay: '2s' }}></div>
        <div className="absolute bottom-1/3 left-1/3 w-1 h-1 bg-zinc-400/30 animate-pulse organic-pulse" style={{ animationDelay: '4s' }}></div>
      </div>
    </div>
  );
};

export default HomePage;

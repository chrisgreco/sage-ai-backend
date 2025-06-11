
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
      gradient: 'from-blue-500 to-purple-600'
    },
    {
      id: 2,
      title: 'Climate Action',
      topic: 'Nuclear vs Renewable Energy',
      participants: 23,
      isLive: true,
      category: 'Environment',
      gradient: 'from-green-500 to-teal-600'
    },
    {
      id: 3,
      title: 'Philosophy',
      topic: 'Free Will vs Determinism',
      participants: 15,
      isLive: false,
      category: 'Philosophy',
      gradient: 'from-purple-500 to-pink-600'
    },
    {
      id: 4,
      title: 'Economics',
      topic: 'Universal Basic Income',
      participants: 31,
      isLive: true,
      category: 'Economics',
      gradient: 'from-yellow-500 to-orange-600'
    },
    {
      id: 5,
      title: 'Politics',
      topic: 'Democracy in Digital Age',
      participants: 8,
      isLive: false,
      category: 'Politics',
      gradient: 'from-red-500 to-pink-600'
    },
    {
      id: 6,
      title: 'Science',
      topic: 'Space Exploration Priority',
      participants: 19,
      isLive: true,
      category: 'Science',
      gradient: 'from-indigo-500 to-blue-600'
    }
  ]);

  const handleStartDebate = () => {
    navigate('/debate/demo');
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Enhanced Background with iOS-style layers */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50/90 via-white/80 to-purple-50/90"></div>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-gradient-to-r from-blue-400/20 to-purple-400/20 rounded-full blur-3xl floating-element"></div>
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-gradient-to-r from-pink-400/20 to-orange-400/20 rounded-full blur-3xl floating-element" style={{ animationDelay: '-3s' }}></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-72 h-72 bg-gradient-to-r from-teal-400/15 to-cyan-400/15 rounded-full blur-3xl floating-element" style={{ animationDelay: '-1.5s' }}></div>
      </div>

      {/* Enhanced iOS-style Header */}
      <div className="glass-panel-elevated sticky top-0 z-50 mx-4 mt-4 mb-6 fade-in-up">
        <div className="max-w-md mx-auto md:max-w-4xl px-6 py-4">
          <div className="flex items-center justify-between">
            <SageLogo size="md" />
            <div className="flex items-center space-x-3">
              {user && <UserMenu />}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Container */}
      <div className="max-w-md mx-auto md:max-w-4xl px-4">
        
        {/* Enhanced Stories Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-content-primary">Live Debates</h2>
            <div className="glass-panel px-3 py-1.5 rounded-full">
              <div className="flex items-center space-x-2 text-sm text-content-secondary">
                <div className="w-2 h-2 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full animate-pulse shadow-lg shadow-green-400/30"></div>
                <span className="font-medium">{featuredRooms.filter(room => room.isLive).length} live</span>
              </div>
            </div>
          </div>
          
          <div className="flex space-x-6 overflow-x-auto pb-6 scrollbar-hide px-3">
            {/* Enhanced Start Debate Story */}
            <div className="flex-shrink-0 cursor-pointer group liquid-morph" onClick={handleStartDebate}>
              <div className="relative story-circle">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 p-1 shadow-2xl shadow-blue-500/25">
                  <div className="w-full h-full rounded-full bg-white/95 backdrop-blur-sm flex items-center justify-center border-2 border-white/50 group-hover:scale-105 transition-all duration-300">
                    <Play className="w-7 h-7 text-slate-800 group-hover:text-blue-600 transition-colors duration-300" />
                  </div>
                </div>
              </div>
              <div className="mt-3 text-center">
                <div className="text-sm font-semibold text-slate-700 truncate w-20">
                  Start
                </div>
              </div>
            </div>

            {/* Enhanced Debate Room Stories */}
            {featuredRooms.map((room) => (
              <DebateStoryCircle key={room.id} room={room} />
            ))}
          </div>
        </div>

        {/* Enhanced Main Feed Area */}
        <div className="space-y-8">
          {/* Enhanced Hero Section */}
          <div className="glass-panel p-8 text-center scale-in liquid-morph">
            <div className="relative">
              <h1 className="text-4xl md:text-5xl font-bold text-gradient mb-4 leading-tight">
                Civil Discourse, Powered by AI
              </h1>
              <p className="text-lg text-content-secondary mb-8 max-w-xl mx-auto leading-relaxed">
                Join thoughtful debates moderated by ancient wisdom. 
                Socrates, Aristotle, and Buddha guide meaningful conversations.
              </p>

              <button 
                onClick={handleStartDebate}
                className="glass-button text-lg px-8 py-4 bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 text-white hover:shadow-2xl hover:shadow-blue-500/25 transition-all duration-500 hover:scale-105 w-full md:w-auto rounded-2xl font-semibold"
              >
                <div className="flex items-center justify-center space-x-3">
                  <Play className="w-5 h-5" />
                  <span>Start a Debate</span>
                </div>
              </button>
            </div>
          </div>

          {/* Enhanced Categories Grid */}
          <div className="glass-panel p-8 liquid-morph">
            <h2 className="text-xl font-semibold text-content-primary mb-6">Explore Topics</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {['Philosophy', 'Technology', 'Politics', 'Science', 'Ethics', 'Economics'].map((category) => (
                <div key={category} className="group cursor-pointer">
                  <div className="glass-panel p-6 hover:bg-white/80 transition-all duration-500 hover:scale-105 hover:shadow-xl hover:shadow-black/10">
                    <h3 className="font-semibold text-content-primary mb-2 text-base">{category}</h3>
                    <div className="flex items-center text-sm text-content-secondary">
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

      {/* Floating ambient particles */}
      <div className="fixed inset-0 pointer-events-none -z-5">
        <div className="absolute top-1/3 left-1/6 w-2 h-2 bg-blue-400/30 rounded-full animate-pulse" style={{ animationDelay: '0s' }}></div>
        <div className="absolute top-2/3 right-1/4 w-1.5 h-1.5 bg-purple-400/30 rounded-full animate-pulse" style={{ animationDelay: '2s' }}></div>
        <div className="absolute bottom-1/3 left-1/3 w-1 h-1 bg-pink-400/30 rounded-full animate-pulse" style={{ animationDelay: '4s' }}></div>
      </div>
    </div>
  );
};

export default HomePage;

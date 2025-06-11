
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
    // For now, navigate to a demo debate room
    // Later this can be enhanced to show room creation modal
    navigate('/debate/demo');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Instagram-style Header */}
      <div className="glass-panel-elevated sticky top-0 z-50 px-4 py-3 mb-4 fade-in-up">
        <div className="max-w-md mx-auto md:max-w-4xl">
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
        
        {/* Stories Section */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-content-primary">Live Debates</h2>
            <div className="flex items-center space-x-2 text-sm text-content-muted">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>{featuredRooms.filter(room => room.isLive).length} live</span>
            </div>
          </div>
          
          <div className="flex space-x-4 overflow-x-auto pb-4 scrollbar-hide px-2">
            {/* Start Debate Story */}
            <div className="flex-shrink-0 cursor-pointer group" onClick={handleStartDebate}>
              <div className="relative">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 p-0.5">
                  <div className="w-full h-full rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center">
                    <Play className="w-6 h-6 text-slate-800" />
                  </div>
                </div>
              </div>
              <div className="mt-2 text-center">
                <div className="text-xs font-medium text-slate-700 truncate w-20">
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
        <div className="space-y-6">
          {/* Hero Section */}
          <div className="glass-panel p-6 text-center scale-in">
            <h1 className="text-3xl md:text-4xl font-bold text-gradient mb-3">
              Civil Discourse, Powered by AI
            </h1>
            <p className="text-base text-content-secondary mb-6 max-w-md mx-auto">
              Join thoughtful debates moderated by ancient wisdom. 
              Socrates, Aristotle, and Buddha guide meaningful conversations.
            </p>

            <button 
              onClick={handleStartDebate}
              className="glass-button text-base px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-xl transition-all duration-300 hover:scale-105 w-full md:w-auto"
            >
              <div className="flex items-center justify-center space-x-2">
                <Play className="w-4 h-4" />
                <span>Start a Debate</span>
              </div>
            </button>
          </div>

          {/* Categories Grid */}
          <div className="glass-panel p-6">
            <h2 className="text-lg font-semibold text-content-primary mb-4">Explore Topics</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {['Philosophy', 'Technology', 'Politics', 'Science', 'Ethics', 'Economics'].map((category) => (
                <div key={category} className="group cursor-pointer">
                  <div className="glass-panel p-4 hover:bg-white/60 transition-all duration-300 hover:scale-105">
                    <h3 className="font-medium text-content-primary mb-1 text-sm">{category}</h3>
                    <div className="flex items-center text-xs text-content-secondary">
                      <Users className="w-3 h-3 mr-1" />
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

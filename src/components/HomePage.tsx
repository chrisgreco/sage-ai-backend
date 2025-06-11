
import React, { useState } from 'react';
import { Play, Users } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import SageLogo from './SageLogo';
import UserMenu from './UserMenu';
import DebateStoryCircle from './DebateStoryCircle';

const HomePage: React.FC = () => {
  const { user } = useAuth();
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="glass-panel-elevated p-6 mb-8 fade-in-up">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <SageLogo size="lg" />
            <div className="flex items-center space-x-4">
              {user && <UserMenu />}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-6">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gradient mb-4">
            Civil Discourse, Powered by AI
          </h1>
          <p className="text-xl text-content-secondary mb-8 max-w-2xl mx-auto">
            Join thoughtful debates moderated by ancient wisdom. 
            Socrates, Aristotle, and Buddha guide meaningful conversations.
          </p>

          {/* CTA Button */}
          <button className="glass-button text-lg px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center space-x-2">
              <Play className="w-5 h-5" />
              <span>Start a Debate</span>
            </div>
          </button>
        </div>

        {/* Live Debates Stories */}
        <div className="glass-panel p-8 mb-8 scale-in">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-semibold text-content-primary">Live Debates</h2>
            <div className="flex items-center space-x-2 text-sm text-content-muted">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>{featuredRooms.filter(room => room.isLive).length} active</span>
            </div>
          </div>
          
          <div className="flex space-x-4 overflow-x-auto pb-4 scrollbar-hide">
            {featuredRooms.map((room) => (
              <DebateStoryCircle key={room.id} room={room} />
            ))}
          </div>
        </div>

        {/* Featured Categories */}
        <div className="glass-panel p-8">
          <h2 className="text-2xl font-semibold text-content-primary mb-6">Explore Topics</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {['Philosophy', 'Technology', 'Politics', 'Science', 'Ethics', 'Economics'].map((category) => (
              <div key={category} className="group cursor-pointer">
                <div className="glass-panel p-6 hover:bg-white/60 transition-all duration-300 hover:scale-105">
                  <h3 className="font-semibold text-content-primary mb-2">{category}</h3>
                  <div className="flex items-center text-sm text-content-secondary">
                    <Users className="w-4 h-4 mr-1" />
                    <span>{Math.floor(Math.random() * 50) + 10} debates</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;

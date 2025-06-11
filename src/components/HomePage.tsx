
import React, { useState } from 'react';
import { Play, Sparkles, Users } from 'lucide-react';
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Header */}
      <div className="relative">
        <div className="absolute inset-0 bg-white/30 backdrop-blur-xl border-b border-white/20"></div>
        <div className="relative max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <SageLogo size="md" />
            <div className="flex items-center space-x-4">
              {user && <UserMenu />}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="mb-6">
            <h1 className="text-5xl font-bold bg-gradient-to-r from-slate-800 via-blue-600 to-purple-600 bg-clip-text text-transparent mb-4">
              Civil Discourse, Powered by AI
            </h1>
            <p className="text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
              Join thoughtful debates moderated by ancient wisdom. 
              Socrates, Aristotle, and Buddha guide meaningful conversations.
            </p>
          </div>

          {/* CTA Button */}
          <button className="group relative px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-2xl font-semibold text-lg shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-700 to-purple-700 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            <div className="relative flex items-center space-x-2">
              <Sparkles className="w-5 h-5" />
              <span>Start a Debate</span>
            </div>
          </button>
        </div>

        {/* Live Debates Stories */}
        <div className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-slate-800">Live Debates</h2>
            <div className="flex items-center space-x-2 text-sm text-slate-600">
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
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {['Philosophy', 'Technology', 'Politics', 'Science', 'Ethics', 'Economics'].map((category) => (
            <div key={category} className="group cursor-pointer">
              <div className="relative overflow-hidden rounded-2xl bg-white/40 backdrop-blur-sm border border-white/30 p-6 hover:bg-white/60 transition-all duration-300 hover:scale-105">
                <div className="absolute inset-0 bg-gradient-to-br from-transparent to-black/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="relative">
                  <h3 className="font-semibold text-slate-800 mb-2">{category}</h3>
                  <div className="flex items-center text-sm text-slate-600">
                    <Users className="w-4 h-4 mr-1" />
                    <span>{Math.floor(Math.random() * 50) + 10} debates</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="text-center mt-16">
          <div className="inline-flex items-center space-x-2 px-6 py-3 bg-white/50 backdrop-blur-sm border border-white/30 rounded-full text-slate-600">
            <Play className="w-4 h-4" />
            <span>Join thousands in meaningful dialogue</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;

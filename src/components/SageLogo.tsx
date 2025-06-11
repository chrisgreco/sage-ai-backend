
import React from 'react';

interface SageLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const SageLogo: React.FC<SageLogoProps> = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24'
  };

  const textSizeClasses = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-3xl',
    xl: 'text-5xl'
  };

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      {/* Organic Triangle Logo with liquid glass effect */}
      <div className={`${sizeClasses[size]} relative icon-container`}>
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Enhanced gradients with organic feel */}
          <defs>
            <linearGradient id="triangleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.95"/>
              <stop offset="50%" stopColor="currentColor" stopOpacity="0.8"/>
              <stop offset="100%" stopColor="currentColor" stopOpacity="0.85"/>
            </linearGradient>
            <filter id="glassFilter">
              <feGaussianBlur in="SourceGraphic" stdDeviation="0.5"/>
              <feOffset dx="0" dy="1" result="offset"/>
              <feFlood floodColor="rgba(255,255,255,0.3)"/>
              <feComposite in2="offset" operator="in"/>
              <feMerge>
                <feMergeNode/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          
          {/* Outer triangle with organic curves */}
          <path
            d="M50 8 C52 8, 54 9, 55 11 L85 72 C86 74, 85 76, 83 77 L17 77 C15 76, 14 74, 15 72 L45 11 C46 9, 48 8, 50 8 Z"
            fill="url(#triangleGradient)"
            className="text-content-primary drop-shadow-lg"
            filter="url(#glassFilter)"
          />
          
          {/* Inner triangle (negative space) with softer curves */}
          <path
            d="M50 22 C51 22, 52 23, 52.5 24 L70 58 C70.5 59, 70 60, 69 60 L31 60 C30 60, 29.5 59, 30 58 L47.5 24 C48 23, 49 22, 50 22 Z"
            fill="white"
            className="opacity-90"
            style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.1))' }}
          />
          
          {/* Top accent line with organic curve */}
          <path
            d="M32 35 C40 34, 60 34, 68 35"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            className="text-content-primary opacity-75"
            style={{ filter: 'drop-shadow(0 1px 1px rgba(255,255,255,0.5))' }}
          />
          
          {/* Subtle highlight for glass effect */}
          <path
            d="M50 12 L48 15 L52 15 Z"
            fill="rgba(255,255,255,0.6)"
            className="opacity-80"
          />
        </svg>
      </div>
      
      {/* SAGE Text with enhanced styling */}
      <span className={`font-bold tracking-tight text-gradient ${textSizeClasses[size]}`}
            style={{ 
              filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.1))',
              letterSpacing: '0.02em'
            }}>
        SAGE
      </span>
    </div>
  );
};

export default SageLogo;

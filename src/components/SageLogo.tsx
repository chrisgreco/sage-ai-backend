
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
      {/* Geometric Triangle Logo */}
      <div className={`${sizeClasses[size]} relative`}>
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Main triangle with glass effect */}
          <defs>
            <linearGradient id="triangleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.9"/>
              <stop offset="100%" stopColor="currentColor" stopOpacity="0.7"/>
            </linearGradient>
          </defs>
          
          {/* Outer triangle */}
          <path
            d="M50 10 L85 75 L15 75 Z"
            fill="url(#triangleGradient)"
            className="text-content-primary drop-shadow-lg"
          />
          
          {/* Inner triangle (negative space) */}
          <path
            d="M50 25 L70 60 L30 60 Z"
            fill="white"
            className="opacity-100"
          />
          
          {/* Top accent line */}
          <path
            d="M30 35 L70 35"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            className="text-content-primary opacity-80"
          />
        </svg>
      </div>
      
      {/* SAGE Text */}
      <span className={`font-bold tracking-tight text-gradient ${textSizeClasses[size]}`}>
        SAGE
      </span>
    </div>
  );
};

export default SageLogo;

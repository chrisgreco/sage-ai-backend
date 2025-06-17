
import React from 'react';

interface SageLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const SageLogo: React.FC<SageLogoProps> = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-7 h-7',
    md: 'w-10 h-10',
    lg: 'w-14 h-14',
    xl: 'w-20 h-20'
  };

  const textSizeClasses = {
    sm: 'text-base',
    md: 'text-xl',
    lg: 'text-2xl',
    xl: 'text-4xl'
  };

  return (
    <div className={`flex items-center space-x-2.5 ${className}`}>
      {/* Refined Triangle Logo with new silver tones */}
      <div className={`${sizeClasses[size]} relative icon-container`}>
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="triangleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#e2e8f0" stopOpacity="0.95"/>
              <stop offset="30%" stopColor="#f1f5f9" stopOpacity="0.9"/>
              <stop offset="70%" stopColor="#cbd5e1" stopOpacity="0.85"/>
              <stop offset="100%" stopColor="#94a3b8" stopOpacity="0.9"/>
            </linearGradient>
            <filter id="glassFilter">
              <feGaussianBlur in="SourceGraphic" stdDeviation="0.3"/>
              <feOffset dx="0" dy="0.5" result="offset"/>
              <feFlood floodColor="rgba(255,255,255,0.4)"/>
              <feComposite in2="offset" operator="in"/>
              <feMerge>
                <feMergeNode/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          
          {/* Refined triangle with new silver gradients */}
          <path
            d="M50 10 C51.5 10, 52.5 10.5, 53 12 L82 68 C82.5 69.5, 82 70.5, 80.5 71 L19.5 71 C18 70.5, 17.5 69.5, 18 68 L47 12 C47.5 10.5, 48.5 10, 50 10 Z"
            fill="url(#triangleGradient)"
            filter="url(#glassFilter)"
          />
          
          {/* Refined inner triangle */}
          <path
            d="M50 24 C50.8 24, 51.2 24.3, 51.5 25 L68 56 C68.3 56.7, 68 57.2, 67.2 57.3 L32.8 57.3 C32 57.2, 31.7 56.7, 32 56 L48.5 25 C48.8 24.3, 49.2 24, 50 24 Z"
            fill="rgba(255,255,255,0.85)"
            style={{ filter: 'drop-shadow(0 0.5px 1px rgba(0,0,0,0.08))' }}
          />
          
          {/* Refined accent line */}
          <path
            d="M34 36 C42 35.5, 58 35.5, 66 36"
            stroke="#cbd5e1"
            strokeWidth="2"
            strokeLinecap="round"
            style={{ filter: 'drop-shadow(0 0.5px 0.5px rgba(255,255,255,0.4))' }}
          />
          
          {/* Subtle highlight */}
          <path
            d="M50 14 L48.5 16 L51.5 16 Z"
            fill="rgba(255,255,255,0.5)"
          />
        </svg>
      </div>
      
      {/* SAGE Text with new silver styling */}
      <span className={`font-medium tracking-wide ${textSizeClasses[size]}`}
            style={{ 
              background: 'linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 30%, #94a3b8 70%, #64748b 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              filter: 'drop-shadow(0 0.5px 1px rgba(0,0,0,0.08))',
              letterSpacing: '0.015em'
            }}>
        SAGE
      </span>
    </div>
  );
};

export default SageLogo;

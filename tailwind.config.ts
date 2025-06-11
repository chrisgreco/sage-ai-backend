
import type { Config } from "tailwindcss";

export default {
	darkMode: ["class"],
	content: [
		"./pages/**/*.{ts,tsx}",
		"./components/**/*.{ts,tsx}",
		"./app/**/*.{ts,tsx}",
		"./src/**/*.{ts,tsx}",
	],
	prefix: "",
	theme: {
		container: {
			center: true,
			padding: '2rem',
			screens: {
				'2xl': '1400px'
			}
		},
		extend: {
			colors: {
				border: 'hsl(var(--border))',
				input: 'hsl(var(--input))',
				ring: 'hsl(var(--ring))',
				background: 'hsl(var(--background))',
				foreground: 'hsl(var(--foreground))',
				primary: {
					DEFAULT: 'hsl(var(--primary))',
					foreground: 'hsl(var(--primary-foreground))'
				},
				secondary: {
					DEFAULT: 'hsl(var(--secondary))',
					foreground: 'hsl(var(--secondary-foreground))'
				},
				destructive: {
					DEFAULT: 'hsl(var(--destructive))',
					foreground: 'hsl(var(--destructive-foreground))'
				},
				muted: {
					DEFAULT: 'hsl(var(--muted))',
					foreground: 'hsl(var(--muted-foreground))'
				},
				accent: {
					DEFAULT: 'hsl(var(--accent))',
					foreground: 'hsl(var(--accent-foreground))'
				},
				popover: {
					DEFAULT: 'hsl(var(--popover))',
					foreground: 'hsl(var(--popover-foreground))'
				},
				card: {
					DEFAULT: 'hsl(var(--card))',
					foreground: 'hsl(var(--card-foreground))'
				},
				glass: {
					primary: 'hsl(var(--glass-primary))',
					secondary: 'hsl(var(--glass-secondary))',
					accent: 'hsl(var(--glass-accent))',
					surface: 'hsl(var(--glass-surface))',
					border: 'hsl(var(--glass-border))',
				},
				content: {
					primary: 'hsl(var(--content-primary))',
					secondary: 'hsl(var(--content-secondary))',
					muted: 'hsl(var(--content-muted))',
					inverse: 'hsl(var(--content-inverse))',
				},
				// Enhanced Liquid Silver Color Palette
				silver: {
					50: 'hsl(var(--platinum-light))',
					100: 'hsl(var(--chrome-light))',
					200: 'hsl(var(--silver-light))',
					300: 'hsl(var(--silver-medium))',
					400: 'hsl(var(--silver-dark))',
					500: 'hsl(var(--chrome-medium))',
					600: 'hsl(var(--platinum-medium))',
					700: 'rgb(100, 116, 139)',
					800: 'rgb(71, 85, 105)',
					900: 'rgb(51, 65, 85)',
				},
				chrome: {
					50: 'hsl(var(--chrome-light))',
					100: 'hsl(var(--silver-light))',
					200: 'hsl(var(--silver-medium))',
					300: 'hsl(var(--chrome-medium))',
					400: 'rgb(148, 163, 184)',
					500: 'rgb(100, 116, 139)',
					600: 'rgb(71, 85, 105)',
				},
				platinum: {
					50: 'hsl(var(--platinum-light))',
					100: 'hsl(var(--platinum-medium))',
					200: 'hsl(var(--silver-light))',
					300: 'hsl(var(--silver-medium))',
					400: 'rgb(203, 213, 225)',
					500: 'rgb(148, 163, 184)',
				}
			},
			borderRadius: {
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 2px)',
				sm: 'calc(var(--radius) - 4px)',
				// Organic liquid silver border radius
				'liquid-xs': '35% 65% 60% 40%',
				'liquid-sm': '40% 60% 55% 45%',
				'liquid-md': '45% 55% 60% 40%',
				'liquid-lg': '50% 50% 45% 55%',
				'liquid-xl': '55% 45% 50% 60%',
				'liquid-2xl': '60% 40% 55% 45%',
			},
			fontFamily: {
				sans: ['SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
				mono: ['SF Mono', 'Monaco', 'Consolas', 'monospace'],
			},
			scale: {
				'102': '1.02',
				'105': '1.05',
				'108': '1.08',
			},
			backdropBlur: {
				xs: '2px',
				'4xl': '32px',
			},
			backdropSaturate: {
				'150': '1.5',
				'175': '1.75',
				'200': '2',
			},
			backdropBrightness: {
				'105': '1.05',
				'110': '1.1',
				'115': '1.15',
			},
			keyframes: {
				'accordion-down': {
					from: {
						height: '0'
					},
					to: {
						height: 'var(--radix-accordion-content-height)'
					}
				},
				'accordion-up': {
					from: {
						height: 'var(--radix-accordion-content-height)'
					},
					to: {
						height: '0'
					}
				},
				'fade-in': {
					'0%': {
						opacity: '0',
						transform: 'translateY(10px)'
					},
					'100%': {
						opacity: '1',
						transform: 'translateY(0)'
					}
				},
				'slide-in-right': {
					'0%': { transform: 'translateX(100%)' },
					'100%': { transform: 'translateX(0)' }
				},
				'pulse-glow': {
					'0%, 100%': {
						boxShadow: '0 0 20px rgba(34, 197, 94, 0.3)'
					},
					'50%': {
						boxShadow: '0 0 30px rgba(34, 197, 94, 0.5)'
					}
				},
				// Enhanced Liquid Silver Animations
				'liquid-morph': {
					'0%': {
						borderRadius: '45% 55% 60% 40%',
						transform: 'scale(1) rotate(0deg)',
					},
					'25%': {
						borderRadius: '60% 40% 45% 55%',
						transform: 'scale(1.01) rotate(0.5deg)',
					},
					'50%': {
						borderRadius: '40% 60% 55% 45%',
						transform: 'scale(0.99) rotate(-0.3deg)',
					},
					'75%': {
						borderRadius: '55% 45% 40% 60%',
						transform: 'scale(1.005) rotate(0.2deg)',
					},
					'100%': {
						borderRadius: '45% 55% 60% 40%',
						transform: 'scale(1) rotate(0deg)',
					}
				},
				'liquid-shimmer': {
					'0%, 100%': {
						opacity: '1',
						transform: 'scale(1) rotate(0deg)',
					},
					'25%': {
						opacity: '0.8',
						transform: 'scale(1.02) rotate(0.5deg)',
					},
					'50%': {
						opacity: '0.9',
						transform: 'scale(0.98) rotate(-0.3deg)',
					},
					'75%': {
						opacity: '0.85',
						transform: 'scale(1.01) rotate(0.2deg)',
					}
				},
				'liquid-text-shimmer': {
					'0%, 100%': {
						backgroundPosition: '0% 50%',
					},
					'50%': {
						backgroundPosition: '100% 50%',
					}
				},
				'organic-pulse': {
					'0%, 100%': {
						borderRadius: '50% 40% 60% 45%',
						transform: 'scale(1) rotate(0deg)',
					},
					'33%': {
						borderRadius: '45% 55% 50% 60%',
						transform: 'scale(1.02) rotate(1deg)',
					},
					'66%': {
						borderRadius: '60% 45% 55% 50%',
						transform: 'scale(0.98) rotate(-0.5deg)',
					}
				},
				'metallic-flow': {
					'0%': {
						backgroundPosition: '0% 50%',
						transform: 'rotate(0deg)',
					},
					'50%': {
						backgroundPosition: '100% 50%',
						transform: 'rotate(1deg)',
					},
					'100%': {
						backgroundPosition: '0% 50%',
						transform: 'rotate(0deg)',
					}
				}
			},
			animation: {
				'accordion-down': 'accordion-down 0.2s ease-out',
				'accordion-up': 'accordion-up 0.2s ease-out',
				'fade-in': 'fade-in 0.6s ease-out',
				'slide-in-right': 'slide-in-right 0.3s ease-out',
				'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
				// Enhanced Liquid Silver Animations
				'liquid-morph': 'liquid-morph 15s ease-in-out infinite',
				'liquid-shimmer': 'liquid-shimmer 12s ease-in-out infinite',
				'liquid-text-shimmer': 'liquid-text-shimmer 8s ease-in-out infinite',
				'organic-pulse': 'organic-pulse 10s ease-in-out infinite',
				'metallic-flow': 'metallic-flow 6s ease-in-out infinite',
				'morph-fast': 'liquid-morph 8s ease-in-out infinite',
				'morph-slow': 'liquid-morph 20s ease-in-out infinite',
			},
			backgroundImage: {
				'liquid-silver': 'linear-gradient(135deg, hsl(var(--silver-light)) 0%, hsl(var(--chrome-medium)) 25%, hsl(var(--platinum-medium)) 50%, hsl(var(--silver-medium)) 75%, hsl(var(--chrome-light)) 100%)',
				'chrome-gradient': 'linear-gradient(135deg, hsl(var(--chrome-light)) 0%, hsl(var(--silver-medium)) 50%, hsl(var(--chrome-medium)) 100%)',
				'platinum-gradient': 'linear-gradient(135deg, hsl(var(--platinum-light)) 0%, hsl(var(--silver-light)) 50%, hsl(var(--platinum-medium)) 100%)',
			}
		}
	},
	plugins: [require("tailwindcss-animate")],
} satisfies Config;

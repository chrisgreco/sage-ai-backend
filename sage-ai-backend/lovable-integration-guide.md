# Lovable Frontend Integration Guide
## Connecting to Sage AI Backend

### 🎯 Backend Server Details
- **Primary Server**: `https://sage-ai-backend-l0en.onrender.com`
- **Health Check**: `https://sage-ai-backend-l0en.onrender.com/health`
- **Status**: ✅ Deployed with environment variables configured

---

## 🚀 Quick Setup Code for Lovable

### 1. API Configuration
```javascript
// API Configuration - Add this to your main config
const API_CONFIG = {
  baseURL: 'https://sage-ai-backend-l0en.onrender.com',
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  }
};

// Backup servers (if needed)
const BACKUP_SERVERS = [
  'https://sage-ai-backend-l0en.onrender.com', // Primary
  // Add backup URLs here if you create them
];
```

### 2. API Client with Error Handling
```javascript
// Create this as a utility file in your Lovable project
class SageAPIClient {
  constructor() {
    this.baseURL = API_CONFIG.baseURL;
    this.currentServerIndex = 0;
  }

  async makeRequest(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...API_CONFIG.headers,
          ...options.headers,
        },
        signal: AbortSignal.timeout(API_CONFIG.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error for ${endpoint}:`, error);
      throw this.handleError(error, endpoint, options);
    }
  }

  handleError(error, endpoint, options) {
    if (error.name === 'AbortError') {
      return new Error('Request timeout - server may be starting up');
    }
    
    if (error.message.includes('CORS')) {
      return new Error('CORS error - backend CORS configuration issue');
    }
    
    if (error.message.includes('Failed to fetch')) {
      return new Error('Network error - check if backend is running');
    }
    
    return error;
  }

  // Health check method
  async checkHealth() {
    return this.makeRequest('/health');
  }

  // LiveKit connection
  async connectToLiveKit() {
    return this.makeRequest('/connect');
  }

  // Create debate room
  async createDebate(topic, roomName = null) {
    return this.makeRequest('/debate', {
      method: 'POST',
      body: JSON.stringify({ topic, room_name: roomName }),
    });
  }
}

// Export for use in your components
const apiClient = new SageAPIClient();
export default apiClient;
```

### 3. React Hook for Backend Connection
```javascript
// Custom hook for managing backend connection
import { useState, useEffect } from 'react';

export function useBackendConnection() {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkConnection();
  }, []);

  const checkConnection = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const health = await apiClient.checkHealth();
      console.log('Backend health:', health);
      
      if (health.status === 'healthy') {
        setIsConnected(true);
        
        // Also check LiveKit availability
        if (health.livekit_available) {
          console.log('✅ LiveKit is available');
        } else {
          console.warn('⚠️ LiveKit not available');
        }
      }
    } catch (err) {
      console.error('Backend connection failed:', err);
      setError(err.message);
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isConnected,
    error,
    isLoading,
    checkConnection,
  };
}
```

### 4. Example Component Implementation
```javascript
// Example debate component for your Lovable app
import React from 'react';
import { useBackendConnection } from './useBackendConnection';
import apiClient from './apiClient';

export function DebateApp() {
  const { isConnected, error, isLoading } = useBackendConnection();
  const [debateData, setDebateData] = useState(null);

  const createDebate = async (topic) => {
    try {
      const result = await apiClient.createDebate(topic);
      console.log('Debate created:', result);
      setDebateData(result);
      
      // Use the LiveKit token and room info
      if (result.token && result.livekit_url) {
        // Connect to LiveKit room here
        connectToLiveKitRoom(result);
      }
    } catch (err) {
      console.error('Failed to create debate:', err);
    }
  };

  if (isLoading) {
    return <div>Connecting to backend...</div>;
  }

  if (error) {
    return (
      <div>
        <p>❌ Backend Error: {error}</p>
        <button onClick={() => window.location.reload()}>
          Retry Connection
        </button>
      </div>
    );
  }

  if (!isConnected) {
    return <div>❌ Backend not available</div>;
  }

  return (
    <div>
      <h1>✅ Connected to Sage AI Backend</h1>
      <button onClick={() => createDebate('AI Ethics in Education')}>
        Start Debate
      </button>
      
      {debateData && (
        <div>
          <p>Room: {debateData.room_name}</p>
          <p>Topic: {debateData.message}</p>
        </div>
      )}
    </div>
  );
}
```

---

## 🔧 Available Backend Endpoints

### Health Check
```javascript
// GET /health
const health = await apiClient.checkHealth();
// Returns: { status: "healthy", livekit_available: true }
```

### LiveKit Connection  
```javascript
// GET /connect
const connection = await apiClient.connectToLiveKit();
// Returns: { status: "success", livekit_url: "...", token: "..." }
```

### Create Debate Room
```javascript
// POST /debate
const debate = await apiClient.createDebate("Your Topic Here");
// Returns: { status: "success", room_name: "...", token: "..." }
```

---

## 🚨 Troubleshooting Guide

### Error: "Primary server unavailable - using backup servers"
**Cause**: Backend is temporarily down or restarting
**Solution**: Wait 2-3 minutes for Render to restart, or implement backup server logic

### Error: "CORS error - backend CORS configuration issue"  
**Cause**: Backend not allowing requests from Lovable domain
**Solution**: ✅ Already fixed - backend allows `https://lovable.dev`

### Error: "Network error - check if backend is running"
**Cause**: Complete network failure or wrong URL
**Solution**: Verify the backend URL is `https://sage-ai-backend-l0en.onrender.com`

### Error: "Request timeout - server may be starting up"
**Cause**: Render cold start (free tier sleeps after inactivity)
**Solution**: Retry after 30-60 seconds

---

## 🎯 Integration Checklist for Lovable

1. ✅ **Copy the API client code** into your Lovable project
2. ✅ **Use the backend URL**: `https://sage-ai-backend-l0en.onrender.com`
3. ✅ **Test health endpoint** first: `/health`
4. ✅ **Handle errors gracefully** with the provided error handling
5. ✅ **Implement the React hook** for connection management
6. ✅ **Test debate creation** with `/debate` endpoint

---

## 🔥 Quick Test Script

```javascript
// Run this in your browser console to test the connection
async function testBackend() {
  try {
    // Test health
    const health = await fetch('https://sage-ai-backend-l0en.onrender.com/health');
    const healthData = await health.json();
    console.log('✅ Health:', healthData);
    
    // Test LiveKit connection
    const connect = await fetch('https://sage-ai-backend-l0en.onrender.com/connect');
    const connectData = await connect.json();
    console.log('✅ LiveKit:', connectData);
    
    // Test debate creation
    const debate = await fetch('https://sage-ai-backend-l0en.onrender.com/debate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: 'Test Topic' })
    });
    const debateData = await debate.json();
    console.log('✅ Debate:', debateData);
    
  } catch (error) {
    console.error('❌ Test failed:', error);
  }
}

// Run the test
testBackend();
```

**Current Status**: Backend is deployed and configured with all necessary environment variables. CORS is properly set for Lovable. Ready for frontend integration! 🚀 
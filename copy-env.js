import fs from 'fs';
import path from 'path';

// Check if .env file exists in livekit-agents directory
const livekitEnvPath = path.join('livekit-agents', '.env');
const destEnvPath = '.env';

if (fs.existsSync(livekitEnvPath)) {
  try {
    console.log(`Copying environment variables from ${livekitEnvPath}...`);
    const envContent = fs.readFileSync(livekitEnvPath, 'utf8');
    fs.writeFileSync(destEnvPath, envContent);
    console.log('Environment variables copied successfully.');
  } catch (error) {
    console.error('Error copying environment variables:', error);
    process.exit(1);
  }
} else {
  console.warn(`Warning: ${livekitEnvPath} not found. No environment variables copied.`);
} 
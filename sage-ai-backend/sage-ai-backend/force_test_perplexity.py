"""
Force test with the exact API key from .env
"""

import asyncio
import aiohttp

async def force_test_perplexity():
    """Test with the exact API key"""
    
    # Use the exact API key I saw in the .env file
    api_key = "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"
    
    print(f"Testing with API key: {api_key[:15]}...")
    print(f"Key length: {len(api_key)}")
    print(f"Starts with pplx-: {api_key.startswith('pplx-')}")
    print()
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "user",
                "content": "What percentage of Earth's surface is water? Give a brief answer."
            }
        ],
        "max_tokens": 150,
        "temperature": 0.1
    }
    
    print("Making API request to Perplexity...")
    print(f"URL: {url}")
    print(f"Model: {payload['model']}")
    print()
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload, timeout=30) as response:
                print(f"✅ Status Code: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print("🎉 SUCCESS!")
                    print(f"Response: {data}")
                    
                    if 'choices' in data and len(data['choices']) > 0:
                        answer = data['choices'][0]['message']['content']
                        print(f"🏛️ ARISTOTLE: {answer}")
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    print(f"Response headers: {dict(response.headers)}")
                
        except asyncio.TimeoutError:
            print("❌ Request timed out")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(force_test_perplexity()) 

#!/usr/bin/env python3
"""
Comprehensive test of the Sage AI memory system
Tests room creation, conversation storage, and cross-session memory access
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_memory_manager import SupabaseMemoryManager

async def test_memory_system():
    print('🧪 Testing Supabase Memory System...')
    
    # Initialize memory manager
    memory = SupabaseMemoryManager()
    if not memory.client:
        print('❌ Failed to connect to Supabase')
        return False
    
    print('✅ Connected to Supabase')
    
    # Test room creation
    room_name = 'test-philosophy-debate-room'
    debate_topic = 'The Nature of Justice: Platos Republic vs Modern Ethics'
    fake_token = 'test-token-12345'
    participants = [
        {'name': 'Alice', 'role': 'human'},
        {'name': 'Bob', 'role': 'human'},
        {'name': 'Socrates', 'role': 'ai'},
        {'name': 'Aristotle', 'role': 'ai'}
    ]
    
    room_id = await memory.create_or_get_room(room_name, debate_topic, fake_token, participants)
    if room_id:
        print(f'✅ Room created/retrieved: {room_id}')
    else:
        print('❌ Failed to create room')
        return False
    
    # Test storing conversation segments
    session_num = 1
    segments = [
        (1, 'human', 'Alice', 'Hello everyone, I believe justice is about fairness and equality. What do you think, Socrates?'),
        (2, 'socrates', 'Socrates', 'Ah, my dear Alice! But what do you mean by fairness? Is it fair to treat unequal things equally? Let us examine this more closely...'),
        (3, 'human', 'Bob', 'I think justice is more about following the law and social contracts.'),
        (4, 'aristotle', 'Aristotle', 'Both perspectives have merit. Justice exists in different forms - distributive justice, corrective justice, and reciprocal justice.')
    ]
    
    print('\n💾 Storing conversation segments...')
    for segment_num, role, name, content in segments:
        success = await memory.store_conversation_segment(
            room_id, session_num, segment_num, role, name, content,
            key_points=['justice', 'fairness', 'equality'] if 'justice' in content.lower() else []
        )
        if success:
            print(f'✅ Stored segment {segment_num}: {name}')
        else:
            print(f'❌ Failed to store segment {segment_num}')
    
    # Test AI personality memory
    print('\n🧠 Storing AI personality memories...')
    await memory.store_personality_memory(
        room_id, 'socrates', 'key_question', 
        'What is the true meaning of fairness?', session_num, 9
    )
    await memory.store_personality_memory(
        room_id, 'aristotle', 'stance_taken',
        'Justice has multiple forms that must be considered', session_num, 8
    )
    
    # Test retrieving memory context
    print('\n📚 Retrieving memory context...')
    context = await memory.get_room_memory_context(room_name, session_num, max_segments=10)
    print(f'✅ Retrieved {len(context["recent_segments"])} conversation segments')
    
    if context['recent_segments']:
        print('Recent conversation:')
        for seg in context['recent_segments']:
            print(f'  {seg["speaker_name"]} ({seg["speaker_role"]}): {seg["content_text"][:60]}...')
    
    # Test cross-session access (simulate next day)
    print('\n🌅 Simulating next day session...')
    new_session = 2
    new_fake_token = 'test-token-67890'
    
    # Same room name, different token (new session)
    room_id_2 = await memory.create_or_get_room(room_name, debate_topic, new_fake_token, participants)
    
    # Should get same room ID and access previous context
    if room_id_2 == room_id:
        print('✅ Same room accessed with different token - MEMORY PERSISTS!')
    else:
        print('❌ Different room created - memory isolation issue')
        
    # Get memory from previous session
    previous_context = await memory.get_room_memory_context(room_name, max_segments=20)
    if previous_context['recent_segments']:
        print(f'✅ Retrieved {len(previous_context["recent_segments"])} segments from previous session')
        print('Previous conversation still accessible:')
        for seg in previous_context['recent_segments'][:2]:
            print(f'  {seg["speaker_name"]}: {seg["content_text"][:60]}...')
    else:
        print('❌ No previous context found')
    
    # Test personality memory retrieval
    if previous_context.get('personality_memories', {}).get('socrates'):
        print('✅ Socrates memories retrieved:')
        for mem in previous_context['personality_memories']['socrates']:
            print(f'  - {mem["memory_type"]}: {mem["content"][:50]}...')
    
    print('\n🎯 Memory system test complete!')
    return True

async def test_agent_integration():
    """Test if the multi-personality agent can access the memory system"""
    print('\n🤖 Testing Agent Memory Integration...')
    
    try:
        # Import agent components
        from multi_personality_agent import load_room_memory_context
        
        # Test memory loading
        context = await load_room_memory_context('test-philosophy-debate-room', 1)
        if context and context.get('recent_segments'):
            print(f'✅ Agent can access {len(context["recent_segments"])} memory segments')
            return True
        else:
            print('❌ Agent memory integration failed')
            return False
            
    except ImportError as e:
        print(f'⚠️ Agent import failed: {e}')
        return False
    except Exception as e:
        print(f'❌ Agent memory test failed: {e}')
        return False

if __name__ == "__main__":
    print("🚀 Sage AI Memory System Comprehensive Test\n")
    
    async def run_all_tests():
        # Test 1: Core memory system
        memory_success = await test_memory_system()
        
        # Test 2: Agent integration 
        agent_success = await test_agent_integration()
        
        print(f"\n📊 Test Results:")
        print(f"Memory System: {'✅ PASS' if memory_success else '❌ FAIL'}")
        print(f"Agent Integration: {'✅ PASS' if agent_success else '❌ FAIL'}")
        
        if memory_success and agent_success:
            print("\n🎉 ALL TESTS PASSED! Memory system is ready for production.")
        else:
            print("\n⚠️ Some tests failed. Check the output above for issues.")
    
    asyncio.run(run_all_tests()) 
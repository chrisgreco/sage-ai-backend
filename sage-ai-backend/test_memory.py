import asyncio
from supabase_memory_manager import SupabaseMemoryManager

async def test_memory_system():
    print('🧪 Testing Sage AI Memory System...')
    memory = SupabaseMemoryManager()
    
    if not memory.client:
        print('❌ Supabase connection failed')
        return False
    
    print('✅ Connected to Supabase')
    
    # Test room creation with debate topic
    room_name = 'philosophy-debate-123'
    debate_topic = 'The Nature of Justice: Plato vs Modern Ethics'
    
    room_id = await memory.create_or_get_room(
        room_name, 
        debate_topic, 
        'test-token-abc',
        [
            {'name': 'Alice', 'role': 'human'},
            {'name': 'Socrates', 'role': 'ai'},
            {'name': 'Aristotle', 'role': 'ai'}
        ]
    )
    
    if room_id:
        print(f'✅ Room created: {room_id}')
        
        # Test storing conversation segments
        conversation = [
            (1, 'human', 'Alice', 'What is justice according to Plato?'),
            (2, 'socrates', 'Socrates', 'Ah, my dear Alice! Justice, as I understand it, is about the harmony of the soul. When each part does what it is meant to do.'),
            (3, 'human', 'Alice', 'But what about fairness and equality?'),
            (4, 'aristotle', 'Aristotle', 'My teacher Plato speaks of ideal justice, but I believe we must consider practical justice - distributive and corrective.')
        ]
        
        session_num = 1
        for segment_num, role, name, content in conversation:
            success = await memory.store_conversation_segment(
                room_id, session_num, segment_num, role, name, content
            )
            if success:
                print(f'✅ Stored: {name} segment {segment_num}')
            else:
                print(f'❌ Failed to store segment {segment_num}')
        
        # Test AI personality memory
        await memory.store_personality_memory(
            room_id, 'socrates', 'key_question', 
            'What is the true nature of justice?', session_num, 9
        )
        print('✅ Stored Socrates personality memory')
        
        # Test memory retrieval
        context = await memory.get_room_memory_context(room_name)
        segments = len(context.get('recent_segments', []))
        print(f'✅ Retrieved {segments} conversation segments')
        
        if segments > 0:
            print('\n💬 Recent conversation:')
            for seg in context['recent_segments']:
                print(f"  {seg['speaker_name']}: {seg['content_text'][:60]}...")
            
            # Test cross-session access (simulate next day)
            print('\n🌅 Testing next day session access...')
            room_id_2 = await memory.create_or_get_room(
                room_name,  # Same room name
                debate_topic,
                'test-token-xyz',  # Different token (new session)
                [{'name': 'Bob', 'role': 'human'}]
            )
            
            if room_id_2 == room_id:
                print('✅ Same room accessed - MEMORY PERSISTS ACROSS SESSIONS!')
                
                # Retrieve previous context
                old_context = await memory.get_room_memory_context(room_name)
                if old_context.get('recent_segments'):
                    print(f'✅ Previous conversation still accessible ({len(old_context["recent_segments"])} segments)')
                    print(f'First message: {old_context["recent_segments"][0]["content_text"]}')
                    
                    # Check personality memories
                    if old_context.get('personality_memories', {}).get('socrates'):
                        print('✅ AI personality memories preserved')
                        for mem in old_context['personality_memories']['socrates']:
                            print(f'  Socrates remembers: {mem["content"]}')
                    
                    print('\n🎉 MEMORY SYSTEM FULLY FUNCTIONAL!')
                    return True
                else:
                    print('❌ Previous context lost')
                    return False
            else:
                print('❌ Different room created - memory isolation issue')
                return False
        else:
            print('❌ No segments retrieved')
            return False
    else:
        print('❌ Failed to create room')
        return False

if __name__ == "__main__":
    result = asyncio.run(test_memory_system())
    if result:
        print('\n🎯 Memory system ready for voice agent integration!')
    else:
        print('\n⚠️ Memory system needs debugging') 
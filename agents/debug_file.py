# test_booking.py
import sys
import os
sys.path.append(os.path.dirname(__file__))

def debug_booking_flow():
    """Debug function to test the booking flow step by step"""
    
    print("=== DEBUGGING BOOKING FLOW ===")
    
    # Test 1: Import the tools
    try:
        from tools.sql_tools import get_available_slots, book_appointment
        print("✓ Tools imported successfully")
    except Exception as e:
        print(f"✗ Tool import failed: {e}")
        return
    
    # Test 2: Get available slots
    try:
        print("\n--- Testing get_available_slots ---")
        slots = get_available_slots.invoke("Apollo Hospital", "General Physician")
        print(f"✓ Found {len(slots)} slots")
        if slots:
            print(f"First slot: {slots[0]}")
    except Exception as e:
        print(f"✗ get_available_slots failed: {e}")
        return
    
    # Test 3: Try booking
    try:
        print("\n--- Testing book_appointment ---")
        if slots and len(slots) > 0:
            slot_id = slots[0]['slot_id']
            print(f"Attempting to book slot ID: {slot_id}")
            result = book_appointment.invoke(slot_id)
            print(f"✓ Booking result: {result}")
        else:
            print("✗ No slots to book")
    except Exception as e:
        print(f"✗ book_appointment failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_booking_flow()
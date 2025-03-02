from llm.client import LLMClient
from playbooks.me_naiset import ME_NAISET_PLAYBOOK

def main():
    # Create a telemarketer instance with the Me Naiset playbook
    telemarketer = LLMClient(playbook=ME_NAISET_PLAYBOOK)
    
    # Start the call
    response = telemarketer.get_response()
    print("AI:", response)
    
    # Simulate a conversation
    while True:
        # Get user input
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit", "lopeta"]:
            break
        elif user_input.lower() == "reset":
            print(telemarketer.reset_conversation())
            response = telemarketer.get_response()
            print("AI:", response)
            continue
            
        # Get AI response
        response = telemarketer.get_response(user_input)
        print("AI:", response)
    
    print("\nCall ended.")

if __name__ == "__main__":
    main()

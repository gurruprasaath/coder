from google import genai

def main():
    # Using the API key provided earlier
    api_key = "AIzaSyD6uKvgyw1CKHNVvgyIfCjzhJX9ZLwmmSQ"
    
    print("Initializing Gemini Client...")
    try:
        client = genai.Client(api_key=api_key)
        
        print("\nAvailable Gemini Models:")
        print("-" * 40)
        
        # In the new google-genai SDK, client.models.list() retrieves the models
        for model in client.models.list():
            # Print the model name (and description if available)
            print(f"- {model.name}")
            
    except Exception as e:
        print(f"Failed to list models. Error: {e}")

if __name__ == "__main__":
    main()

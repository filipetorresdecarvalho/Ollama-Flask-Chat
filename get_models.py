import json
import re
import subprocess

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

def fetch_ollama_models():
    """
    Fetches installed Ollama models. It tries the Python library first,
    but falls back to the command line if the library fails or returns an empty list.
    """
    # Method 1: Try the library first
    if OLLAMA_AVAILABLE:
        try:
            print("Attempting to fetch models via Ollama library...")
            ollama_models_raw = ollama.list().get('models', [])
            models = [{'name': m.get('name')} for m in ollama_models_raw if m.get('name')]
            
            # If the library returns a non-empty list, use it.
            if models:
                print(f"Success: Found {len(models)} models via the library.")
                return models
            # If the library returns an empty list, log it and proceed to fallback.
            else:
                print("Warning: Ollama library returned an empty list. Proceeding to command-line fallback.")

        except Exception as e:
            print(f"Ollama library call failed: {e}. Trying command line as fallback.")
    else:
        print("Ollama library not installed. Using command line.")

    # Method 2: Fallback to command line
    try:
        print("Attempting to fetch models via command line...")
        result = subprocess.run(
            ['ollama', 'list'], capture_output=True, text=True, check=True, encoding='utf-8'
        )
        lines = result.stdout.strip().split('\n')
        model_list = []
        if len(lines) > 1:
            for line in lines[1:]:  # Skip header
                parts = re.split(r'\s{2,}', line)  # Split on 2 or more spaces
                if parts:
                    model_list.append({'name': parts[0].strip()})
        
        if model_list:
            print(f"Success: Found {len(model_list)} models via the command line.")
        
        return model_list
    except (FileNotFoundError, subprocess.CalledProcessError) as sub_e:
        print(f"Error: Ollama command line call failed: {sub_e}")
        return [] # Return empty list on failure

def save_models_to_json(models):
    """Saves the list of models to models.json."""
    try:
        with open('models.json', 'w') as f:
            json.dump(models, f, indent=4)
        print(f"Successfully saved {len(models)} models to models.json")
    except Exception as e:
        print(f"Error: Could not write to models.json. {e}")

if __name__ == '__main__':
    models = fetch_ollama_models()
    if models:
        save_models_to_json(models)
    else:
        print("Final result: No Ollama models were found by any method.")
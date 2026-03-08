from utils.langfuse_tracker import tracker

def main():
    if not tracker.is_enabled:
        print("Langfuse is not enabled")
        return
    
    client = tracker.get_client()
    print("Client:", type(client))
    if hasattr(client, "start_as_current_observation"):
        print("start_as_current_observation exists!")
    else:
        print("start_as_current_observation missing!")

if __name__ == "__main__":
    main()

from inference import chat

if __name__ == "__main__":
    print("bmo is up!")
    while True:
        msg = input("> ")
        if msg.lower() in ("quit", "exit"):
            break
        print(chat(msg))

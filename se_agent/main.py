# main.py
from se_agent.github_listener import run_server

def main():
    """
    Entry point for the Software Engineering Agent.
    Starts the GitHub webhook listener server.
    """
    run_server()

if __name__ == "__main__":
    main()
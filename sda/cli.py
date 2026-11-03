import os, sys, subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: sda [command] [options]")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "streamlit":
        base_dir = os.path.dirname(os.path.abspath(__file__))
        streamlit_dir = os.path.join(base_dir, "streamlit")
        script = os.path.join(streamlit_dir, "streamlit.py")

        os.chdir(streamlit_dir)
        result = subprocess.run([sys.executable, "-P", "-m", "streamlit", "run", script] + args)
        sys.exit(result.returncode)
    else:
        print(f"Unkown command: {cmd}")
        print(f"Possible commands: streamlit")
        sys.exit(1)

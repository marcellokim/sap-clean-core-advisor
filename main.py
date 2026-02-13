"""CLI 진입점 (개발/디버깅용)."""

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    """Streamlit 앱을 CLI에서 실행."""
    import subprocess
    import sys

    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)


if __name__ == "__main__":
    main()

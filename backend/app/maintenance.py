"""Run bounded retention periodically while Render is awake; never promise always-on work."""
import logging,time
from .jobs import retain

def main():
    while True:
        try:retain();logging.info('Retention completed')
        except Exception:logging.error('Retention failed; inspect database health')
        time.sleep(6*60*60)
if __name__=='__main__':main()

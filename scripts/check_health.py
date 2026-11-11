"""Check both public origins and send a bounded, sanitized SMTP incident alert."""
import json
import os
import ssl
import smtplib
import time
import urllib.request
from email.message import EmailMessage


def check():
    failed=[]
    for origin in ('https://biteai-demo.onrender.com', 'https://restaurant-management-system-qxtx.vercel.app'):
        healthy=False
        for attempt in range(3):
            try:
                with urllib.request.urlopen(origin+'/api/health', timeout=60) as response:
                    result=json.load(response)
                healthy=result.get('status')=='ok' and result.get('database')=='connected'
            except Exception:
                pass
            if healthy:break
            if attempt<2:time.sleep(10)
        if not healthy:failed.append(origin)
    if not failed:return
    if not os.getenv('SMTP_PASSWORD'):
        raise SystemExit('Health check failed; SMTP alert credentials are missing')
    message=EmailMessage()
    message['From']='letsbiteai@gmail.com'
    message['To']='letsbiteai@gmail.com'
    message['Subject']='BiteAI health check failed'
    message.set_content('These BiteAI origins failed three health checks:\n'+'\n'.join(failed)+'\nInspect Render and GitHub Actions logs. Render Free may need time to wake.')
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com',465,timeout=20,context=ssl.create_default_context()) as smtp:
            smtp.login('letsbiteai@gmail.com',os.environ['SMTP_PASSWORD'])
            smtp.send_message(message)
    except Exception:
        raise SystemExit('Health check failed and alert delivery failed') from None
    raise SystemExit('Health check failed; incident email sent')


if __name__=='__main__':check()

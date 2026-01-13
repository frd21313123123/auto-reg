import requests
import time
import sys

API_URL = "https://api.mail.tm"

def get_token(email, password):
    """Получаем токен доступа"""
    try:
        payload = {"address": email, "password": password}
        response = requests.post(f"{API_URL}/token", json=payload)
        if response.status_code == 200:
            return response.json()['token']
        else:
            print("[-] Ошибка авторизации. Проверьте email и пароль.")
            return None
    except Exception as e:
        print(f"[-] Ошибка сети: {e}")
        return None

def get_message_content(msg_id, token):
    """Получаем текст письма"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_URL}/messages/{msg_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('text') or data.get('html') or "Пустое сообщение"
    except:
        return "Ошибка чтения"

def watch_inbox(email, password):
    print(f"[*] Вход в почту: {email}...")
    token = get_token(email, password)
    if not token:
        return

    print(f"[+] Успешный вход. Ожидание новых писем (Ctrl+C для выхода)...")
    
    headers = {"Authorization": f"Bearer {token}"}
    processed_ids = set()
    
    # Сначала загружаем существующие, чтобы не спамить ими, или показываем их сразу
    # Для простоты просто начнем цикл
    
    try:
        while True:
            try:
                response = requests.get(f"{API_URL}/messages", headers=headers)
                if response.status_code == 200:
                    messages = response.json()['hydra:member']
                    
                    # Проверяем новые сообщения
                    for msg in messages:
                        if msg['id'] not in processed_ids:
                            processed_ids.add(msg['id'])
                            
                            # Детали письма
                            sender = msg['from']['address']
                            subject = msg['subject']
                            date = msg['createdAt']
                            
                            print("\n" + "="*50)
                            print(f"НОВОЕ ПИСЬМО!")
                            print(f"От: {sender}")
                            print(f"Тема: {subject}")
                            print("-" * 20)
                            
                            # Получаем полный текст
                            content = get_message_content(msg['id'], token)
                            print(content)
                            print("="*50 + "\n")
                            
            except Exception as e:
                print(f"[!] Ошибка проверки: {e}")
            
            time.sleep(3) # Проверка каждые 3 секунды
            
    except KeyboardInterrupt:
        print("\n[*] Работа завершена.")

if __name__ == "__main__":
    print("--- Чтение почты Mail.tm ---")
    
    if len(sys.argv) == 3:
        # Можно запустить: python listener.py email password
        email_arg = sys.argv[1]
        pass_arg = sys.argv[2]
        watch_inbox(email_arg, pass_arg)
    else:
        # Или ввести вручную
        email_in = input("Введите Email: ").strip()
        pass_in = input("Введите Пароль: ").strip()
        watch_inbox(email_in, pass_in)

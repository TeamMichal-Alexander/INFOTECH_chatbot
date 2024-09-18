import paramiko
import requests
from requests import RequestException


def create_ssh_tunnel(remote_host, remote_port, local_port, ssh_host, ssh_port, ssh_user, ssh_key=None,
                      ssh_password=None):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if ssh_key:
        ssh_client.connect(ssh_host, port=ssh_port, username=ssh_user, key_filename=ssh_key)
    else:
        ssh_client.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password)

    transport = ssh_client.get_transport()
    channel = transport.open_channel(
        'direct-tcpip',
        (remote_host, remote_port),
        ('127.0.0.1', local_port)
    )

    print(f"Tunnel established from localhost:{local_port} to {remote_host}:{remote_port}")
    return channel

def send_api_request(api_url, headers=None, data=None):
    """Отправка HTTP-запроса к API через локальный порт"""
    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        print(response.text)
        return response.json()
    except RequestException as e:
        print(f"Ошибка при отправке запроса: {e}")
        return None



if __name__ == "__main__":
    api_url = "http://localhost:9999/api/generate"
    headers = {"Content-Type": "application/json"}
    data = {
        "prompt": "Why is sky blue?",
        "model": "llama3.1",
        "stream": False
    }

    response = send_api_request(api_url, headers=headers, data=data)

    print("Результат API:", response)

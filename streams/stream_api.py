#!/usr/bin/python3

from flask import Flask, Response
import time
import json
import random
import socket

app = Flask(__name__)

@app.route('/stream')
def stream():
    def generate():
        while True:
            data = {
                'timestamp': time.time(),
                'value': random.randint(1, 100)
            }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)  # Send data every second

    return Response(generate(), mimetype='text/event-stream')

def get_ip_addresses():
    ip_addresses = []
    interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
    for interface in interfaces:
        ip_addresses.append(interface[4][0])
    return list(set(ip_addresses))  # Remove duplicates

if __name__ == '__main__':
    ip_addresses = get_ip_addresses()
    print("Server is running. You can access it at:")
    for ip in ip_addresses:
        print(f"http://{ip}:5000/stream")
    print("http://localhost:5000/stream")
    print("\n\n")
    app.run(host='0.0.0.0', port=5000, debug=False)


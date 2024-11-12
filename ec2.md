# Deploying se-agent on AWS EC2

1. instantiate an EC2 instance
2. ssh into the instance
3. build python 3.12 from source
4. install git
5. install nginx
6. clone se-agent repo
7. install se-agent dependencies
8. setup .env
9. install gunicorn
10. Run se-agent flask using gunicorn
11. setup gunicon service (to start se-agent on boot)
12. setup nginx
13. run gunicon service
14. run nginx
15. tail logs

## gunicorn

1. Install gunicorn

    ```bash
    pip install gunicorn
    ```

2. Create a new file:

    ```bash
    sudo nano /etc/systemd/system/gunicorn.service
    ```

3. Add the following content:

    ```bash
    [Unit]
    Description=Gunicorn instance to serve Flask app
    After=network.target

    [Service]
    User=ec2-user
    Group=ec2-user
    WorkingDirectory=/home/ec2-user/work/se-agent
    Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/ec2-user/se-agent/bin"
    Environment="PYTHONPATH=/home/ec2-user/work/se-agent"
    Environment="HOME=/home/ec2-user"
    ExecStart=/home/ec2-user/se-agent/bin/gunicorn --workers 3 --bind 0.0.0.0:3000 --timeout 300 se_agent.flask_server:app

    [Install]
    WantedBy=multi-user.target
    ```

    Enable and start service:
    ```bash
    sudo systemctl start gunicorn
    sudo systemctl enable gunicorn
    ```

    Later for any changes in the service file, reload the service:

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl restart gunicorn
    ```

## nginx

1. Open the main Nginx configuration file:

    ```bash
    sudo nano /etc/nginx/nginx.conf
    ```
2. Add the following content:

    ```bash
        server {
	listen 80;
        listen [::]:80;
        server_name _;

        location / {
            proxy_pass http://127.0.0.1:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
        }

	error_page 404 /404.html;
        location = /404.html {
        }

	error_page 500 502 503 504 /50x.html;
        location = /50x.html {
        }
    }
    ```

3. Test & restart Nginx:

    ```bash
    sudo nginx -t
    sudo systemctl restart nginx
    ```

# Tail logs

1. To tail se-agent logs

    ```bash
    sudo journalctl -u gunicorn -f
    ```

2. To check last 100 lines of gunicorn logs

    ```bash
    sudo journalctl -u gunicorn -n 100
    ```

# IBM Internal Deployment Details

## Provision a new virtual machine

> https://ocp-draco.bx.cloud9.ibm.com/iaas/CreateVM

This requires linkage to a Research Challenge

## Install Python 3.12

SE-agent uses python 3.12.

To install that we first need to enable the Extra Packages for Enterprise Linux (EPEL) repository. `sudo dnf install -y epel-release` didn't work, so I had to manually download and install EPEL.

```bash
sudo /usr/bin/crb enable
sudo dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
```

After this I was able to directly install python3.12 as follows:

```bash
sudo dnf module enable python:3.12
```

I verified the installation with:

```bash
python3.12 --version
```

Upgraded `pip` with:

```bash
python3.12 -m pip install --upgrade pip
```

and updated python3 to point to python3.12:

```bash
sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
sudo alternatives --config python3
```

## Create a virtual environment and activate it

```bash
python3.12 -m venv se-agent-env
source se-agent-env/bin/activate
```

## Setup environment configurations

```bash
cp example.env .env
# and edit .env!
```

## Setup gunicorn to run SE agent as a service

1. Install gunicorn

    ```bash
    source se-agent-env/bin/activate
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
    User=root
    Group=root
    WorkingDirectory=/root/se-agent
    Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/se-agent-env/bin"
    Environment="PYTHONPATH=/root/se-agent"
    Environment="HOME=/root"
    ExecStart=/root/se-agent-env/bin/gunicorn --workers 10 --bind 0.0.0.0:3000 --timeout 600 se_agent.flask_server:app

    [Install]
    WantedBy=multi-user.target
    ```

    Note: number of workers may be chosen based on 
    $$
    \text{Number of Workers} = 2 \times (\text{Number of CPU Cores}) + 1
    $$


4. Enable and start service:

    ```bash
    sudo systemctl start gunicorn
    sudo systemctl enable gunicorn
    ```

    Later for any changes in the service file, reload the service as follows:

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl restart gunicorn
    ```

## Tail logs

1. To tail se-agent logs

    ```bash
    sudo journalctl -u gunicorn -f
    ```

2. To check last 100 lines of gunicorn logs

    ```bash
    sudo journalctl -u gunicorn -n 100
    ```

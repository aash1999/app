sudo tee /etc/systemd/system/flask.service > /dev/null <<'EOF'
[Unit]
Description=Gunicorn instance to serve Flask app
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/app
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF



### Service start

sudo tee /etc/systemd/system/flask.service > /dev/null <<'EOF'
[Unit]
Description=Gunicorn instance to serve Flask app
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/app
ExecStart=/home/ec2-user/.local/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always
Environment="PATH=/home/ec2-user/.local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOF


####
sudo tee /etc/systemd/system/flask.service > /dev/null <<'EOF'
[Unit]
Description=Gunicorn instance to serve Flask app
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/app
Environment="AWS_DEFAULT_REGION=us-east-2"
ExecStart=/home/ec2-user/.local/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app

[Install]
WantedBy=multi-user.target
EOF


sudo systemctl daemon-reload
sudo systemctl enable flask
sudo systemctl restart flask
sudo systemctl status flask
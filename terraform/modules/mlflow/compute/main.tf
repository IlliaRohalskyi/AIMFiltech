# IAM role for EC2
resource "aws_iam_role" "mlflow_ec2_role" {
  name = "mlflow-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "ec2.amazonaws.com"
        },
        Effect = "Allow",
        Sid   = ""
      },
    ]
  })

  tags = {
    Name = "MLflow EC2 Role"
  }
}

resource "aws_iam_role_policy_attachment" "mlflow_ec2_s3_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
  role       = aws_iam_role.mlflow_ec2_role.name
}

resource "aws_iam_role_policy_attachment" "mlflow_ec2_rds_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonRDSFullAccess"
  role       = aws_iam_role.mlflow_ec2_role.name
}

resource "aws_iam_instance_profile" "mlflow_ec2_profile" {
  name = "mlflow-ec2-profile"
  role = aws_iam_role.mlflow_ec2_role.name
}

# Get latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-amd64-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] 
}

# SSH key pair
resource "aws_key_pair" "mlflow_key" {
  key_name   = var.key_name
  public_key = file("~/.ssh/id_rsa.pub") # Replace with your public key path
}

resource "aws_instance" "mlflow_ec2" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.ec2_instance_type
  key_name               = var.key_name
  vpc_security_group_ids = var.vpc_security_group_ids
  subnet_id              = var.subnet_id
  associate_public_ip_address = true
  iam_instance_profile   = aws_iam_instance_profile.mlflow_ec2_profile.name

  root_block_device {
    encrypted = true
  }

  user_data = <<-EOF
              #!/bin/bash
              set -e

              # Update system and install dependencies
              sudo apt update
              sudo apt install -y python3-pip nginx software-properties-common apache2-utils

              # Install Python packages required for MLflow
              pip3 install werkzeug==2.2.3 flask==2.2.3 click==8.1.3
              pip3 install importlib-metadata>=4.0.0
              pip3 install mlflow==2.8.0 boto3 psycopg2-binary

              # Create a startup script for MLflow
              cat <<EOT > /home/ubuntu/start_mlflow.sh
              #!/bin/bash
              mlflow server -h 127.0.0.1 -p 5000 \
              --backend-store-uri postgresql://${var.mlflow_db_username}:${var.mlflow_db_password}@${var.rds_address}:5432/mlflowdb?sslmode=require \
              --default-artifact-root s3://${var.s3_bucket_name}
              EOT

              chmod +x /home/ubuntu/start_mlflow.sh
              sudo chown ubuntu:ubuntu /home/ubuntu/start_mlflow.sh

              # Configure MLflow to start with the system
              cat <<EOT > /etc/systemd/system/mlflow.service
              [Unit]
              Description=MLflow Tracking Server
              After=network.target

              [Service]
              User=ubuntu
              WorkingDirectory=/home/ubuntu
              ExecStart=/home/ubuntu/start_mlflow.sh
              Restart=always

              [Install]
              WantedBy=multi-user.target
              EOT

              sudo systemctl daemon-reload
              sudo systemctl enable mlflow.service
              sudo systemctl start mlflow.service

              # Generate self-signed SSL certificate
              sudo mkdir -p /etc/nginx/ssl
              sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                  -keyout /etc/nginx/ssl/selfsigned.key \
                  -out /etc/nginx/ssl/selfsigned.crt \
                  -subj "/CN=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)"

              sudo htpasswd -bc /etc/nginx/.htpasswd "${var.mlflow_basic_auth_user}" "${var.mlflow_basic_auth_password}"

              # Configure NGINX to use SSL with self-signed certificate and basic auth
              cat <<EOT > /etc/nginx/sites-available/mlflow
              server {
                  listen 443 ssl;
                  server_name $(curl -s http://169.254.169.254/latest/meta-data/public-hostname);

                  ssl_certificate /etc/nginx/ssl/selfsigned.crt;
                  ssl_certificate_key /etc/nginx/ssl/selfsigned.key;

                  location / {
                      auth_basic "Restricted";
                      auth_basic_user_file /etc/nginx/.htpasswd;
                      proxy_pass http://127.0.0.1:5000;
                      proxy_set_header Host \$host;
                      proxy_set_header X-Real-IP \$remote_addr;
                      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
                  }
              }

              server {
                  listen 80;
                  server_name $(curl -s http://169.254.169.254/latest/meta-data/public-hostname);

                  # Redirect all HTTP traffic to HTTPS
                  return 301 https://\$host\$request_uri;
              }
              EOT

              # Update NGINX configuration to fix server_names_hash_bucket_size issue
              sudo sed -i '/http {/a \\    server_names_hash_bucket_size 128;' /etc/nginx/nginx.conf

              sudo ln -s /etc/nginx/sites-available/mlflow /etc/nginx/sites-enabled/mlflow
              sudo systemctl restart nginx
              EOF

  tags = {
    Name = "MLflow Tracking Server"
  }
}
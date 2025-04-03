terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.82.2"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Example budget, unchanged
resource "aws_budgets_budget" "budget" {
  name         = "budget"
  budget_type  = "COST"
  limit_amount = "100"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
}

# S3 bucket resource
resource "aws_s3_bucket" "aimfiltech_training_bucket" {
  bucket = "aimfiltech-training-bucket"
  acl    = "private"

  versioning {
    enabled = true
  }

  tags = {
    Project     = "aimfiltech"
    Environment = "Production"
  }
}

# Data source to gather all files in the ../data folder:
data "local_file" "files" {
  for_each = fileset("${path.module}/../data", "*")

  # 'filename' is the full path, e.g., "/home/user/myproject/data/filename.csv"
  filename = "${path.module}/../data/${each.value}"
}

# Create an S3 bucket object for each file
resource "aws_s3_bucket_object" "add_training_data" {
  for_each = data.local_file.files

  bucket = aws_s3_bucket.aimfiltech_training_bucket.id

  # For the "key" (the destination path in S3), you can use one of the following:
  # Option A: Just the base name of the file
  key = basename(data.local_file.files[each.key].filename)

  # Or Option B: Mirror the entire relative path if desired:
  # key = "some-subfolder/${each.key}"

  # The 'source' attribute points to the exact file path on disk
  source = data.local_file.files[each.key].filename

  acl    = "private"
}

resource "aws_vpc" "mlflow_vpc" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true
  tags = {
    Name = "MLflow VPC"
  }
}

resource "aws_internet_gateway" "mlflow_igw" {
  vpc_id = aws_vpc.mlflow_vpc.id

  tags = {
    Name = "MLflow Internet Gateway"
  }
}

resource "aws_subnet" "mlflow_public_subnet" {
  vpc_id     = aws_vpc.mlflow_vpc.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"

  map_public_ip_on_launch = true

  tags = {
    Name = "MLflow Public Subnet"
  }
}

resource "aws_route_table" "mlflow_public_rt" {
  vpc_id = aws_vpc.mlflow_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.mlflow_igw.id
  }

  tags = {
    Name = "MLflow Public Route Table"
  }
}

resource "aws_route_table_association" "mlflow_public_rt_assoc" {
  subnet_id      = aws_subnet.mlflow_public_subnet.id
  route_table_id = aws_route_table.mlflow_public_rt.id
}

# FIXED: Updated security group with egress rules and SSH access
resource "aws_security_group" "ec2_sg" {
  name        = "mlflow-ec2-sg"
  description = "Security group for MLflow EC2 instance"
  vpc_id      = aws_vpc.mlflow_vpc.id

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] 
    description = "Allow access to MLflow UI"
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] 
    description = "Allow SSH access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "mlflow-ec2-sg"
  }
}

# Create a new VPC for the RDS instance
resource "aws_vpc" "mlflow_rds_vpc" {
  cidr_block = "10.1.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true
  tags = {
    Name = "MLflow RDS VPC"
  }
}

# Create a subnet for the RDS instance
resource "aws_subnet" "mlflow_rds_subnet_a" {
  vpc_id     = aws_vpc.mlflow_rds_vpc.id
  cidr_block = "10.1.1.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "MLflow RDS Subnet"
  }
}

resource "aws_subnet" "mlflow_rds_subnet_b" {
  vpc_id = aws_vpc.mlflow_rds_vpc.id
  cidr_block = "10.1.2.0/24"
  availability_zone = "${var.aws_region}b"

  tags = {
    Name = "MLflow RDS Subnet"
  }
}

# Create a DB subnet group
resource "aws_db_subnet_group" "mlflow_db_subnet_group" {
  name       = "mlflow-db-subnet-group"
  subnet_ids = [aws_subnet.mlflow_rds_subnet_a.id, aws_subnet.mlflow_rds_subnet_b.id]

  tags = {
    Name = "MLflow DB Subnet Group"
  }
}

resource "aws_vpc_peering_connection" "mlflow_vpc_peering" {
  vpc_id      = aws_vpc.mlflow_vpc.id
  peer_vpc_id = aws_vpc.mlflow_rds_vpc.id
  auto_accept = true

  tags = {
    Name = "MLflow VPC Peering"
  }
}

# FIXED: Create a dedicated route table for RDS VPC
resource "aws_route_table" "mlflow_rds_rt" {
  vpc_id = aws_vpc.mlflow_rds_vpc.id

  tags = {
    Name = "MLflow RDS Route Table"
  }
}

# FIXED: Associate the RDS subnets with the RDS route table
resource "aws_route_table_association" "mlflow_rds_rt_assoc_a" {
  subnet_id      = aws_subnet.mlflow_rds_subnet_a.id
  route_table_id = aws_route_table.mlflow_rds_rt.id
}

resource "aws_route_table_association" "mlflow_rds_rt_assoc_b" {
  subnet_id      = aws_subnet.mlflow_rds_subnet_b.id
  route_table_id = aws_route_table.mlflow_rds_rt.id
}

# FIXED: Create routes for VPC peering using the correct route tables
resource "aws_route" "ec2_route" {
  route_table_id            = aws_route_table.mlflow_public_rt.id
  destination_cidr_block    = aws_vpc.mlflow_rds_vpc.cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.mlflow_vpc_peering.id
}

resource "aws_route" "rds_route" {
  route_table_id            = aws_route_table.mlflow_rds_rt.id
  destination_cidr_block    = aws_vpc.mlflow_vpc.cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.mlflow_vpc_peering.id
}

# FIXED: Add internet access for RDS VPC
resource "aws_internet_gateway" "mlflow_rds_igw" {
  vpc_id = aws_vpc.mlflow_rds_vpc.id

  tags = {
    Name = "MLflow RDS Internet Gateway"
  }
}

# FIXED: Add internet route for RDS VPC
resource "aws_route" "rds_internet_route" {
  route_table_id         = aws_route_table.mlflow_rds_rt.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.mlflow_rds_igw.id
}

resource "aws_security_group" "rds_sg" {
  name        = "mlflow-rds-sg"
  description = "Security group for MLflow RDS instance"
  vpc_id      = aws_vpc.mlflow_rds_vpc.id

  # Allow inbound PostgreSQL traffic from the EC2 security group
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
    description     = "Allow PostgreSQL access from EC2 instance"
  }
  
  # ADDED: Egress rule for RDS security group
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  
  tags = {
    Name = "MLflow RDS Security Group"
  }
}

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

# S3 Bucket for Artifact Storage
resource "aws_s3_bucket" "mlflow_bucket" {
  bucket = var.s3_bucket_name
  acl    = "private"

  versioning {
    enabled = true
  }

  tags = {
    Name = "MLflow Artifact Bucket"
  }
}

resource "aws_db_instance" "mlflow_rds" {
  identifier           = "mlflowdb"
  db_name              = "mlflowdb"
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "17.2"
  instance_class       = var.rds_instance_class
  username             = var.mlflow_db_username
  password             = var.mlflow_db_password
  skip_final_snapshot  = true
  db_subnet_group_name = aws_db_subnet_group.mlflow_db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  publicly_accessible = false
}

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

resource "aws_key_pair" "mlflow_key" {
  key_name   = var.key_name
  public_key = file("~/.ssh/id_rsa.pub") # Replace with your public key path
}

resource "aws_instance" "mlflow_ec2" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.ec2_instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  subnet_id              = aws_subnet.mlflow_public_subnet.id
  associate_public_ip_address = true
  iam_instance_profile = aws_iam_instance_profile.mlflow_ec2_profile.name

  user_data = <<-EOF
              #!/bin/bash
              sudo apt update
              sudo apt install -y python3-pip
              
              # Install specific versions of dependencies
              pip3 install werkzeug==2.2.3 flask==2.2.3 click==8.1.3
              pip3 install importlib-metadata>=4.0.0
              pip3 install mlflow==2.8.0 boto3 psycopg2-binary
              
              # Create a simple startup script
              cat <<EOT > /home/ubuntu/start_mlflow.sh
              #!/bin/bash
              mlflow server -h 0.0.0.0 -p 5000 \
              --backend-store-uri postgresql://${var.mlflow_db_username}:${var.mlflow_db_password}@${aws_db_instance.mlflow_rds.address}:5432/mlflowdb \
              --default-artifact-root s3://${aws_s3_bucket.mlflow_bucket.bucket}
              EOT
              
              chmod +x /home/ubuntu/start_mlflow.sh
              sudo chown ubuntu:ubuntu /home/ubuntu/start_mlflow.sh
              
              # Setup to run on startup using a simple systemd service
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
              EOF

  tags = {
    Name = "MLflow Tracking Server"
  }
}


# ADDED: Outputs for accessing the MLflow server
output "mlflow_server_public_dns" {
  description = "Public DNS of the MLflow tracking server"
  value       = aws_instance.mlflow_ec2.public_dns
}

output "mlflow_server_public_ip" {
  description = "Public IP of the MLflow tracking server"
  value       = aws_instance.mlflow_ec2.public_ip
}

output "mlflow_url" {
  description = "URL to access MLflow UI"
  value       = "http://${aws_instance.mlflow_ec2.public_dns}:5000"
}
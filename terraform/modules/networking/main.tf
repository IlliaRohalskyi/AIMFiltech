# Main VPC
resource "aws_vpc" "vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "MLflow VPC"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "mlflow_igw" {
  vpc_id = aws_vpc.vpc.id
  tags = {
    Name = "MLflow Internet Gateway"
  }
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags = {
    Name = "Public Subnet"
  }
}

resource "aws_subnet" "private_subnet_a" {
  vpc_id            = aws_vpc.vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}a"
  tags = {
    Name = "Private Subnet"
  }
}

resource "aws_subnet" "private_subnet_b" {
  vpc_id           = aws_vpc.vpc.id
  cidr_block       = "10.0.3.0/24"
  availability_zone = "${var.aws_region}b"
  tags = {
    Name = "Private Subnet"
  }
}

# Public Route Table
resource "aws_route_table" "mlflow_public_rt" {
  vpc_id = aws_vpc.vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.mlflow_igw.id
  }
  tags = {
    Name = "MLflow Public Route Table"
  }
}

# Associate Public Route Table with Public Subnet
resource "aws_route_table_association" "mlflow_public_rt_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.mlflow_public_rt.id
}

# Private Route Table
resource "aws_route_table" "mlflow_private_rt" {
  vpc_id = aws_vpc.vpc.id
  tags = {
    Name = "MLflow Private Route Table"
  }
}

# Associate Private Route Table with Private Subnet
resource "aws_route_table_association" "mlflow_private_rt_assoc_a" {
  subnet_id      = aws_subnet.private_subnet_a.id
  route_table_id = aws_route_table.mlflow_private_rt.id
}

resource "aws_route_table_association" "mlflow_private_rt_assoc_b" {
  subnet_id      = aws_subnet.private_subnet_b.id
  route_table_id = aws_route_table.mlflow_private_rt.id
}

# Security Group for MLflow (EC2)
resource "aws_security_group" "mlflow_ec2_sg" {
  name        = "mlflow-ec2-sg"
  description = "Security group for MLflow EC2 instance"
  vpc_id      = aws_vpc.vpc.id

  # Allow HTTPS traffic to MLflow
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS traffic to MLflow UI"
  }

  # Allow SSH access only from trusted IPs
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["37.4.229.184/32"]
    description = "Allow SSH access from trusted IPs"
  }

  # Allow all outbound traffic
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

# Security Group for RDS
resource "aws_security_group" "mlflow_rds_sg" {
  name        = "mlflow-rds-sg"
  description = "Security group for MLflow RDS instance"
  vpc_id      = aws_vpc.vpc.id

  # Allow PostgreSQL access from MLflow EC2
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.mlflow_ec2_sg.id]
    description     = "Allow PostgreSQL access from MLflow EC2"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "mlflow-rds-sg"
  }
}

# DB Subnet Group for RDS
resource "aws_db_subnet_group" "mlflow_db_subnet_group" {
  name       = "mlflow-db-subnet-group"
  subnet_ids = [aws_subnet.private_subnet_a.id, aws_subnet.private_subnet_b.id]
  tags = {
    Name = "MLflow DB Subnet Group"
  }
}

# Security Group for AWS Batch
resource "aws_security_group" "batch_sg" {
  name        = "batch-sg"
  description = "Security group for AWS Batch Compute Environment"
  vpc_id      = aws_vpc.vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 0
    to_port   = 65535
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "allow_https_from_private_subnets" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/16"] 
  security_group_id = aws_security_group.batch_sg.id
}

# Create an Elastic IP for the NAT Gateway
resource "aws_eip" "nat_eip" {
  domain = "vpc"
}

# Create a NAT Gateway in the public subnet
resource "aws_nat_gateway" "nat_gateway" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet.id
  
  tags = {
    Name = "MLflow NAT Gateway"
  }
}

# Add route to the private route table
resource "aws_route" "private_nat_route" {
  route_table_id         = aws_route_table.mlflow_private_rt.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat_gateway.id
}
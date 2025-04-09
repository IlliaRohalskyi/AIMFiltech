# Main MLflow VPC
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

resource "aws_security_group" "ec2_sg" {
  name        = "mlflow-ec2-sg"
  description = "Security group for MLflow EC2 instance"
  vpc_id      = aws_vpc.mlflow_vpc.id

  # Allow HTTPS traffic to MLflow
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow HTTPS from anywhere
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

# RDS VPC
resource "aws_vpc" "mlflow_rds_vpc" {
  cidr_block = "10.1.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true
  tags = {
    Name = "MLflow RDS VPC"
  }
}

# RDS Subnets
resource "aws_subnet" "mlflow_rds_subnet_a" {
  vpc_id     = aws_vpc.mlflow_rds_vpc.id
  cidr_block = "10.1.1.0/24"
  availability_zone = "${var.aws_region}a"
  tags = {
    Name = "MLflow RDS Subnet A"
  }
}

resource "aws_subnet" "mlflow_rds_subnet_b" {
  vpc_id = aws_vpc.mlflow_rds_vpc.id
  cidr_block = "10.1.2.0/24"
  availability_zone = "${var.aws_region}b"
  tags = {
    Name = "MLflow RDS Subnet B"
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "mlflow_db_subnet_group" {
  name       = "mlflow-db-subnet-group"
  subnet_ids = [aws_subnet.mlflow_rds_subnet_a.id, aws_subnet.mlflow_rds_subnet_b.id]
  tags = {
    Name = "MLflow DB Subnet Group"
  }
}

# VPC Peering
resource "aws_vpc_peering_connection" "mlflow_vpc_peering" {
  vpc_id      = aws_vpc.mlflow_vpc.id
  peer_vpc_id = aws_vpc.mlflow_rds_vpc.id
  auto_accept = true
  tags = {
    Name = "MLflow VPC Peering"
  }
}

# RDS Route Table
resource "aws_route_table" "mlflow_rds_rt" {
  vpc_id = aws_vpc.mlflow_rds_vpc.id
  tags = {
    Name = "MLflow RDS Route Table"
  }
}

# RDS Route Table Associations
resource "aws_route_table_association" "mlflow_rds_rt_assoc_a" {
  subnet_id      = aws_subnet.mlflow_rds_subnet_a.id
  route_table_id = aws_route_table.mlflow_rds_rt.id
}

resource "aws_route_table_association" "mlflow_rds_rt_assoc_b" {
  subnet_id      = aws_subnet.mlflow_rds_subnet_b.id
  route_table_id = aws_route_table.mlflow_rds_rt.id
}

# VPC Peering Routes
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

# RDS Internet Gateway
resource "aws_internet_gateway" "mlflow_rds_igw" {
  vpc_id = aws_vpc.mlflow_rds_vpc.id
  tags = {
    Name = "MLflow RDS Internet Gateway"
  }
}

# RDS Internet Route
resource "aws_route" "rds_internet_route" {
  route_table_id         = aws_route_table.mlflow_rds_rt.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.mlflow_rds_igw.id
}

# RDS Security Group
resource "aws_security_group" "rds_sg" {
  name        = "mlflow-rds-sg"
  description = "Security group for MLflow RDS instance"
  vpc_id      = aws_vpc.mlflow_rds_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
    description     = "Allow PostgreSQL access from EC2 instance"
  }
  
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
# VPC Module - Creates networking infrastructure

# Create VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "mate-${var.environment}-vpc"
    Environment = var.environment
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "mate-${var.environment}-igw"
    Environment = var.environment
  }
}

# Elastic IP for NAT Gateway (single NAT for cost savings in sandbox)
resource "aws_eip" "nat" {
  count  = 1  # Single NAT Gateway for all AZs (saves ~$90/month)
  domain = "vpc"

  tags = {
    Name        = "mate-${var.environment}-nat-eip"
    Environment = var.environment
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "mate-${var.environment}-public-${var.availability_zones[count.index]}"
    Environment = var.environment
    Type        = "public"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name        = "mate-${var.environment}-private-${var.availability_zones[count.index]}"
    Environment = var.environment
    Type        = "private"
  }
}

# NAT Gateway (single NAT for cost savings)
resource "aws_nat_gateway" "main" {
  count         = 1  # Single NAT Gateway in first public subnet
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name        = "mate-${var.environment}-nat"
    Environment = var.environment
  }

  depends_on = [aws_internet_gateway.main]
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "mate-${var.environment}-public-rt"
    Environment = var.environment
  }
}

# Private Route Table (single table for all private subnets using one NAT)
resource "aws_route_table" "private" {
  count  = 1  # Single route table for all private subnets
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[0].id
  }

  tags = {
    Name        = "mate-${var.environment}-private-rt"
    Environment = var.environment
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[0].id  # All private subnets use the single route table
}

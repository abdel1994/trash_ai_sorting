# Basis security group
resource "aws_security_group" "this" {
  name        = var.name
  description = var.description
  vpc_id      = var.vpc_id

  tags = {
    Name = var.name
  }
}

# Ingress via CIDR
resource "aws_vpc_security_group_ingress_rule" "cidr_ports" {
  for_each = var.ingress_protocol == "-1" ? toset([]) : toset(var.ingress_cidr_blocks)

  security_group_id = aws_security_group.this.id
  cidr_ipv4         = each.value
  from_port         = var.ingress_from_port
  to_port           = var.ingress_to_port
  ip_protocol       = var.ingress_protocol
}

# Ingress via CIDR all
resource "aws_vpc_security_group_ingress_rule" "cidr_all" {
  for_each = var.ingress_protocol == "-1" ? toset(var.ingress_cidr_blocks) : toset([])

  security_group_id = aws_security_group.this.id
  cidr_ipv4         = each.value
  ip_protocol       = "-1"
}

# Ingress via security group
resource "aws_vpc_security_group_ingress_rule" "sg_ports" {
  count = var.create_ingress_from_sg && var.ingress_protocol != "-1" ? 1 : 0

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = var.ingress_source_security_group_id
  from_port                    = var.ingress_from_port
  to_port                      = var.ingress_to_port
  ip_protocol                  = var.ingress_protocol
}

# Ingress via security group all
resource "aws_vpc_security_group_ingress_rule" "sg_all" {
  count = var.create_ingress_from_sg && var.ingress_protocol == "-1" ? 1 : 0

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = var.ingress_source_security_group_id
  ip_protocol                  = "-1"
}

# Egress alles
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.this.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

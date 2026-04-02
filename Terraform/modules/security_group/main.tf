resource "aws_security_group" "this" {
  name        = var.name
  description = var.description
  vpc_id      = var.vpc_id

  tags = {
    Name = var.name
  }
}

resource "aws_vpc_security_group_ingress_rule" "cidr" {
  for_each = toset(var.ingress_cidr_blocks)

  security_group_id = aws_security_group.this.id
  cidr_ipv4         = each.value
  from_port         = var.ingress_from_port
  to_port           = var.ingress_to_port
  ip_protocol       = var.ingress_protocol
}

resource "aws_vpc_security_group_ingress_rule" "sg" {
  count = var.create_ingress_from_sg ? 1 : 0

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = var.ingress_source_security_group_id
  from_port                    = var.ingress_from_port
  to_port                      = var.ingress_to_port
  ip_protocol                  = var.ingress_protocol
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.this.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
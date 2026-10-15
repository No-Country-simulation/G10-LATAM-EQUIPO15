terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.50, < 5.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id                 = var.subscription_id
  use_cli                         = true
  resource_provider_registrations = "none"
  resource_providers_to_register  = ["Microsoft.Compute", "Microsoft.Network"]
}

variable "subscription_id" {
  type = string
}
variable "location" {
  type = string
}
variable "vm_size" {
  type = string
  validation {
    condition = contains([
      "Standard_D2as_v5", "Standard_D2s_v5", "Standard_D2as_v6",
      "Standard_D2s_v6", "Standard_B2ms"
    ], var.vm_size)
    error_message = "Usar uno de los perfiles x64 de 2 vCPU y 8 GB comprobados por el script."
  }
}
variable "admin_cidr" {
  type = string
  validation {
    condition     = can(cidrhost(var.admin_cidr, 0)) && can(regex("^[0-9.]+/32$", var.admin_cidr))
    error_message = "SSH requiere una IPv4 concreta con /32."
  }
}
variable "ssh_public_key" {
  type = string
  validation {
    condition     = startswith(var.ssh_public_key, "ssh-ed25519 ")
    error_message = "Indicar solo la clave publica ED25519."
  }
}
variable "image_version" {
  type = string
}

locals {
  name = "nuevamente-demo"
  tags = { proyecto = "NuevaMente", uso = "trabajo-practico", gestion = "Terraform" }
}

resource "azurerm_resource_group" "app" {
  name     = "${local.name}-rg"
  location = var.location
  tags     = local.tags
}

resource "azurerm_virtual_network" "app" {
  name                = "${local.name}-vnet"
  address_space       = ["10.42.0.0/16"]
  resource_group_name = azurerm_resource_group.app.name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_subnet" "app" {
  name                 = "app"
  resource_group_name  = azurerm_resource_group.app.name
  virtual_network_name = azurerm_virtual_network.app.name
  address_prefixes     = ["10.42.1.0/24"]
}

resource "azurerm_network_security_group" "app" {
  name                = "${local.name}-nsg"
  resource_group_name = azurerm_resource_group.app.name
  location            = var.location
  tags                = local.tags
  security_rule {
    name                       = "SSH-administracion"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.admin_cidr
    destination_address_prefix = "*"
  }
  security_rule {
    name                       = "Web-demo"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }
}

resource "azurerm_public_ip" "app" {
  name                    = "${local.name}-ip"
  resource_group_name     = azurerm_resource_group.app.name
  location                = var.location
  allocation_method       = "Static"
  # La generacion sin SSE puede tardar hasta 650 s en el proxy de la aplicacion.
  idle_timeout_in_minutes = 15
  sku                     = "Standard"
  tags                    = local.tags
}

resource "azurerm_network_interface" "app" {
  name                = "${local.name}-nic"
  resource_group_name = azurerm_resource_group.app.name
  location            = var.location
  tags                = local.tags
  ip_configuration {
    name                          = "app"
    subnet_id                     = azurerm_subnet.app.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.app.id
  }
}

resource "azurerm_network_interface_security_group_association" "app" {
  network_interface_id      = azurerm_network_interface.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}

resource "azurerm_linux_virtual_machine" "app" {
  name                            = "${local.name}-vm"
  resource_group_name             = azurerm_resource_group.app.name
  location                        = var.location
  size                            = var.vm_size
  admin_username                  = "azureuser"
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.app.id]
  custom_data                     = base64encode(file("${path.module}/cloud-init.yaml"))
  tags                            = local.tags
  admin_ssh_key {
    username   = "azureuser"
    public_key = var.ssh_public_key
  }
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = 64
  }
  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = var.image_version
  }
  depends_on = [azurerm_network_interface_security_group_association.app]
}

resource "azurerm_virtual_machine_extension" "ssh_host_key" {
  name                       = "ssh-host-key"
  virtual_machine_id         = azurerm_linux_virtual_machine.app.id
  publisher                  = "Microsoft.Azure.Extensions"
  type                       = "CustomScript"
  type_handler_version       = "2.1"
  auto_upgrade_minor_version = true
  settings = jsonencode({
    commandToExecute = "cat /etc/ssh/ssh_host_ed25519_key.pub"
  })
  tags = local.tags
}

output "public_ip" {
  value = azurerm_public_ip.app.ip_address
}
output "app_url" {
  value = "http://${azurerm_public_ip.app.ip_address}"
}
output "vm_name" {
  value = azurerm_linux_virtual_machine.app.name
}
output "resource_group" {
  value = azurerm_resource_group.app.name
}
output "host_key_extension_id" {
  value = azurerm_virtual_machine_extension.ssh_host_key.id
}

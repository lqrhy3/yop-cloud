# Yop-Cloud

## Description
A simple personal cloud on Raspberry Pi with two SSDs. Store files, run backups, and access via web or WebDAV.

## Requirements
- Raspberry Pi 4 (4 GB+ RAM)  
- Two SSDs on USB 3.0  
- Raspberry Pi OS Lite (64-bit)  
- Docker & Docker Compose  

## Quick Start
1. **Update OS**  
   ```bash
   sudo apt update && sudo apt upgrade -y && sudo reboot
   ```

2. Deploy
   ```bash
   git clone https://github.com/youruser/yop-cloud.git ~/yop-cloud
   cd ~/yop-cloud
   docker-compose up -d
   ```

## License
Feel free to use and modify these instructions for your own use.
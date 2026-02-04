# Object-Detection — Docker Installation Guide

Official repository:
- https://github.com/UTCsilvaluc/Object-Detection.git

This guide explains how to install and run the Object-Detection system with Docker.
No manual configuration of PostgreSQL, Nginx, or system services is required.

---

## 1. Why Docker is used in this project

This project is fully deployed using **Docker Compose**. Docker automatically manages:

- the web application (Flask + Gunicorn)
- the PostgreSQL database
- the Nginx reverse proxy and media serving
- persistent data volumes

### Main advantages

- no manual PostgreSQL installation
- no system Nginx configuration
- no systemd services to maintain
- reproducible deployment
- automatic restart after reboot
- database and media persistence
- clean separation between the system and the application

---

## 2. System requirements

Ubuntu-based VPS or server.

Install required tools:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable docker
sudo systemctl start docker
```

If the installation above does not work, use the alternative method below:

```bash
# Install dependencies
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Register Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
```

Source:
- https://qiita.com/kujiraza/items/a8236f65e2c46735ee91

---

## 3. Download the project

Make sure Git is installed:

```bash
git clone https://github.com/UTCsilvaluc/Object-Detection.git
cd Object-Detection
```

---

## 4. Docker environment configuration

The project uses the following file:

```
.env.docker
```

This file is already provided in the repository. Typical content:

```env
DB_HOST=db
DB_PORT=5432
DB_NAME=object_detection
DB_USER=object_admin
DB_PASSWORD=change_me

MEDIA_ROOT=/data/media
TEMP_ROOT=/data/media/temp
MEDIA_URL=/media

FLASK_ENV=production
FLASK_DEBUG=0
SERVE_MEDIA_WITH_FLASK=0

TORCH_NUM_THREADS=4
OMP_NUM_THREADS=4
MKL_NUM_THREADS=4
```

No additional configuration is required for a standard installation.

---

## 5. Install the SAM model

The system uses **Segment Anything (SAM)**. The checkpoint must be downloaded manually.

### 5.1 Create the checkpoints directory

From the project root:

```bash
mkdir -p checkpoints
cd checkpoints
```

### 5.2 Download the SAM ViT-L model

```bash
wget -O sam_vit_l.pth https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth
```

### 5.3 Important: file name

The application expects the checkpoint file name without the version suffix
(e.g. `sam_vit_l.pth`, `sam_vit_h.pth`).

If needed, rename the file:

```bash
mv sam_vit_l_0b3195.pth sam_vit_l.pth
```

### 5.4 List of official SAM checkpoints

All official models are available here:
- https://github.com/facebookresearch/segment-anything?tab=readme-ov-file#model-checkpoints

If you use a different checkpoint, make sure the expected file name in the code matches.

---

## 6. Start the application

From the project root:

```bash
docker compose --env-file .env.docker up -d --build
```

This starts:

- web (Flask + Gunicorn)
- nginx
- db (PostgreSQL)

---

## 7. Access the application

Open in your browser:

```
http://<SERVER_IP>/
```

(port 80)

---

## 8. Database initialization

The database is:

- automatically created
- automatically initialized

The following SQL files are executed automatically at the first startup:

- create.sql
- index.sql
- insert.sql

No manual database operation is required.

The database is stored in a persistent Docker volume.

---

## 9. Automatic startup after reboot

All services use:

```
restart: unless-stopped
```

Docker itself is enabled at boot:

```bash
systemctl is-enabled docker
```

Therefore:

- after a VPS reboot, all services are restarted automatically

---

## 10. Internal architecture

```
nginx  → reverse proxy and /media
web    → Flask + Gunicorn
db     → PostgreSQL
```

Nginx directly serves:

```
/media/*
```

from the Docker volume.

---

## 11. Important usage rules

- do not start Gunicorn manually
- do not create systemd services for the application
- do not install PostgreSQL on the host system
- always use Docker Compose

---

## 12. Basic health checks

Check container status:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs -f web
```

View database logs:

```bash
docker compose logs -f db
```

Check database tables:

```bash
docker compose exec db psql -U object_admin -d object_detection -c "\\dt"
```

---

## 13. Debugging guide

### 13.1 502 Bad Gateway

Most common reason: the web container crashed.

```bash
docker compose logs web
```

### 13.2 Error: SAM checkpoint not found

Error message:

```
SAM checkpoint not found: /app/checkpoints/sam_vit_l.pth
```

Verify that the checkpoint is visible inside the container:

```bash
docker compose exec web ls /app/checkpoints
```

If empty:

- make sure the directory `checkpoints/` exists at the root of the project
- make sure the following line exists in `docker-compose.yml` under the `web` service:

```yaml
./checkpoints:/app/checkpoints:ro
```

Then recreate the container:

```bash
docker compose up -d --force-recreate web
```

### 13.3 Application loads but analysis fails after upload

Usually caused by:

- missing SAM checkpoint
- wrong file name
- memory or model loading error

Check logs:

```bash
docker compose logs --tail=200 web
```

### 13.4 Database appears empty

```bash
docker compose exec db psql -U object_admin -d object_detection -c "\\dt"
```

If no tables are present, check database initialization logs:

```bash
docker compose logs db
```

### 13.5 Reset the database completely

Warning: this deletes all stored data.

```bash
docker compose down -v
docker compose up -d
```

---

## 14. Network and reverse-proxy debugging

Verify that Nginx can reach the web container:

```bash
docker compose exec nginx wget -O- http://web:5000/
```

---

## 15. Useful commands

| Action      | Command                      |
| ----------- | ---------------------------- |
| Start       | docker compose up -d         |
| Rebuild     | docker compose up -d --build |
| Stop        | docker compose down          |
| Logs (web)  | docker compose logs -f web   |
| Restart web | docker compose restart web   |

---

## 16. One-shot installation summary

```bash
git clone https://github.com/UTCsilvaluc/Object-Detection.git
cd Object-Detection

mkdir -p checkpoints
cd checkpoints
wget -O sam_vit_l.pth https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth
cd ..

docker compose --env-file .env.docker up -d --build
```

No additional steps are required.


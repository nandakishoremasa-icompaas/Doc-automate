# PolicyCollate Pro Engine

## 📖 What This Application Does
If you have a Google Drive folder containing dozens (or hundreds) of individual Google Doc files, combining them manually is a nightmare. 

**PolicyCollate Pro** is an automated web application that solves this. You simply provide a source folder and a blank target document. The engine will:
1. Automatically scan the Drive folder to find every single Google Document.
2. Open your target Master Document and generate a brand-new **Tabbed Interface**.
3. Create a perfectly named tab for every single file in the folder.
4. Seamlessly copy the entire contents (including perfect formatting and images) from the source files and paste them into their respective tabs in the Master Document.

It features a sleek **Web Dashboard** (`app.py`) where you can monitor the live progress, track errors, and watch the system automatically heal itself if Google Docs tries to block it.

## 🚀 Running with Docker

This application has been fully Dockerized. Because it requires Google Chrome and your active Google Login session, we use Docker Compose to mount your local Chrome profile into the container.

### Step 1: Initial Setup
You must have Docker and Docker Compose installed on your system.

### Step 2: Visible Mode & X11 Forwarding (Optional)
Because a Docker container is a headless server, it does not have a physical screen. If you want to use the **"Visible Mode"** toggle in the UI to watch the robot work, you must grant Docker permission to stream video to your Linux monitor.

Run this command in your host terminal **before** starting Docker:
```bash
xhost +local:docker
```
*(You only need to run this command once per reboot).*

### Step 3: Start the Application
Start the Docker container by running:
```bash
docker-compose up --build
```

### Step 4: Access the Dashboard
Once the server is running, open your web browser and navigate to:
**http://localhost:5000**

## ⚠️ Important Notes
- **Google Login**: The `docker-compose.yml` mounts your local `./chrome_profile` directory. If the robot asks for a Google Login, run the script once in Visible Mode to manually log in, and the session will be saved permanently.
- **Headless Mode**: If you are running this on a remote server without a monitor, ALWAYS ensure the "Visible Mode" toggle in the dashboard is turned OFF.

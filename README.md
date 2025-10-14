# 🧠 Object Detection & Metadata Visualization System

This project analyzes images to automatically detect and segment all visible objects using modern computer vision models (YOLOv8, Faster R-CNN, and SAM). It then stores all extracted information and metadata in a PostgreSQL database, allowing structured visualization through a Flask web interface.

---

## 🚀 Features

- **Automatic object detection** (YOLOv8)
- **Segmentation masks** with **Segment Anything Model (SAM)**
- **Metadata extraction and normalization**
- **Image and JSON storage paths automatically standardized**
- **Flask web app** for visualization:
  - `/gallery`: view all uploaded images
  - `/viewer`: view detailed metadata after clicking on an image

---

## ⚙️ Installation Guide

1️⃣ **Clone the repository, create a virtual environment, install dependencies, download SAM, configure the database, and run the app — all steps below in sequence:**

```bash
# Clone the repository
git clone https://github.com/<your-username>/object-detection.git
cd object-detection

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
#Please use pip install or you can use the provided 'requirements.txt' file:
pip install -r requirements.txt
pip install flask psycopg2-binary python-dotenv ultralytics torch torchvision torchaudio regex opencv-python pillow matplotlib numpy

# Download the SAM checkpoint
# The Segment Anything Model (SAM) requires a pretrained checkpoint file.
# Download the file sam_vit_h.pth from the official Meta AI repository:
# 👉 https://github.com/facebookresearch/segment-anything#model-checkpoints
# Then place it inside your project folder:
mkdir -p checkpoints
mv /path/to/sam_vit_h.pth checkpoints/sam_vit_h.pth

# PostgreSQL Database Setup
# Ensure PostgreSQL is installed on your system, then create the database and tables:
createdb -U postgres object_detection
psql -U postgres -d object_detection -f db/create.sql

# Configure environment variables
# Create a .env file at the root of the project with the following content:
echo "DB_NAME=object_detection
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432" > .env

# Run the Flask Application
flask run

# Once running, open your browser and go to:
# http://127.0.0.1:5000

#-------------------------------------------

# Japanese version :
# 物体検出 & メタデータ可視化システム

このプロジェクトは、画像内のすべての可視オブジェクトを自動的に検出・セグメント化する最新のコンピュータビジョンモデル（YOLOv8、Faster R-CNN、SAM）を使用しています。その後、抽出された情報とメタデータをPostgreSQLデータベースに保存し、FlaskのWebインターフェースを通じて構造化された可視化を可能にします。

---

## 機能

- **自動オブジェクト検出**（YOLOv8）
- **セグメンテーションマスク**（Segment Anything Model, SAM）
- **メタデータ抽出と正規化**
- **画像およびJSONの保存パスを自動で標準化**
- **Flask Webアプリでの可視化**:
  - `/gallery`：アップロードされたすべての画像を表示
  - `/viewer`：画像をクリック後に詳細メタデータを表示

---

## インストールガイド

**リポジトリをクローンし、仮想環境を作成、依存関係をインストール、SAMをダウンロード、データベースを設定、アプリを実行 — 以下の手順に従ってください:**

```bash
# リポジトリをクローン
git clone https://github.com/<your-username>/object-detection.git
cd object-detection

# 仮想環境を作成して有効化
python3 -m venv venv
source venv/bin/activate

# 依存関係をインストール
# pipで直接インストールするか、提供されている'requirements.txt'を使用してください:
pip install -r requirements.txt
pip install flask psycopg2-binary python-dotenv ultralytics torch torchvision torchaudio regex opencv-python pillow matplotlib numpy

# SAMチェックポイントのダウンロード
# Segment Anything Model (SAM)には事前学習済みのチェックポイントファイルが必要です。
# 公式Meta AIリポジトリからsam_vit_h.pthをダウンロード:
# https://github.com/facebookresearch/segment-anything#model-checkpoints
# ダウンロード後、プロジェクトフォルダ内に配置:
mkdir -p checkpoints
mv /path/to/sam_vit_h.pth checkpoints/sam_vit_h.pth

# PostgreSQLデータベース設定
# PostgreSQLがシステムにインストールされていることを確認し、データベースとテーブルを作成:
createdb -U postgres object_detection
psql -U postgres -d object_detection -f db/create.sql

# 環境変数の設定
# プロジェクトルートに.envファイルを作成し、以下を記述:
echo "DB_NAME=object_detection
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432" > .env

# Flaskアプリケーションを実行
flask run

# 実行後、ブラウザでアクセス:
# http://127.0.0.1:5000

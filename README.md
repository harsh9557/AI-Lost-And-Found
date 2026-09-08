# 🔎 AI Lost & Found

> An AI-powered Lost & Found Management System built with Python and Streamlit.

## 🚀 About the Project

AI Lost & Found is a smart platform that helps users report lost and found items and find possible matches using Artificial Intelligence.

The system compares item details such as name, description, color, location, and uploaded images to calculate a possible match score.

## ✨ Features

- 🔐 User Login & Sign Up
- 📌 Report Lost Items
- 📦 Report Found Items
- 🤖 AI-Based Item Matching
- 📝 Text Similarity Matching
- 📸 Image Similarity Matching
- 🔔 Automatic Match Notifications
- 🤝 Claim Request System
- 💬 Private Chat After Claim Approval
- 📂 My Reports
- 📊 Dashboard & Analytics
- 👨‍💼 Admin Panel
- 🖼️ Image Upload Support

## 🧠 AI Matching

The matching system uses:

- TF-IDF
- Cosine Similarity
- Perceptual Hashing (pHash)

### Match Score

- Text similarity → 70%
- Image similarity → 30%

Text matching considers:

- Item Name → 35%
- Description → 25%
- Color → 15%
- Location → 25%

A match score of **50% or higher** is treated as a possible match.

## 🛠️ Technologies Used

- Python
- Streamlit
- SQLite
- Scikit-learn
- Pillow
- ImageHash

## 📁 Project Structure

```text
AI-Lost-And-Found/
│
├── app.py
├── ai_matching.py
├── database.py
├── requirements.txt
└── logo.png

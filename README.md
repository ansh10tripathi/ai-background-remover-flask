# AI Background Remover

An AI-powered web application that removes the background from images using Python and Flask.
The application uses the **rembg deep learning model** to automatically detect the foreground and remove the background with high accuracy.

Users can upload an image, process it using AI, compare the original and processed image side-by-side, and download the result.

---

## 🚀 Features

* Drag & Drop Image Upload
* Image Preview before Processing
* AI-Based Background Removal
* Side-by-Side Image Comparison
* Download Processed Image
* Clean and Simple User Interface

---

## 🛠 Tech Stack

### Backend

* Python
* Flask

### AI Processing

* rembg
* ONNX Runtime

### Frontend

* HTML
* CSS
* JavaScript

### Image Processing

* Pillow

---

## 📂 Project Structure

```
ai-background-remover-flask
│
├── app.py
│
├── static
│   ├── style.css
│   ├── uploads
│   └── outputs
│
└── templates
    └── index.html
```

---

## ⚙ Installation

### 1. Clone the Repository

```
git clone https://github.com/YOUR_USERNAME/ai-background-remover-flask.git
```

### 2. Navigate to the Project Folder

```
cd ai-background-remover-flask
```

### 3. Create a Virtual Environment

```
python -m venv venv
```

### 4. Activate the Virtual Environment

**Windows**

```
venv\Scripts\activate
```

**Mac / Linux**

```
source venv/bin/activate
```

### 5. Install Dependencies

```
pip install flask rembg pillow onnxruntime
```

### 6. Run the Application

```
python app.py
```

### 7. Open in Browser

```
http://127.0.0.1:5000
```

---

## 📸 How It Works

1. User uploads an image.
2. The image is sent to the Flask backend.
3. The **rembg AI model** processes the image.
4. Background is removed automatically.
5. The processed image is displayed and can be downloaded.

---

## 🖼 Example Workflow

Upload Image → AI Processing → Background Removed → Download Result

---

## 🔮 Future Improvements

* Background Replacement
* Background Blur Effect
* Batch Image Processing
* Drag Comparison Slider
* Image Enhancement using AI
* Cloud Deployment

---

## 📚 Learning Outcomes

This project helped in understanding:

* Flask Web Development
* AI Image Processing
* Python Backend Integration
* Frontend Interaction with Backend
* Building AI-based Web Applications

---

## 👨‍💻 Author

**Ansh Tripathi**
BTech CSE (AI/ML)

---

## ⭐ Support

If you like this project, consider giving it a **star ⭐ on GitHub**.

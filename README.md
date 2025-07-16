# 🎯 SlideGenie

Transform your research into professional presentations in seconds!

## 🚀 Features

- **AI-Powered**: Convert research content to structured presentations using OpenAI
- **Multiple Input Types**: Support for abstracts, bullet points, and full text
- **Presentation Templates**: Choose from various academic and professional styles
- **Customizable**: Adjust slide count and presentation type
- **Research-Focused**: Built specifically for academic and research presentations

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/slidegenie.git
cd slidegenie
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your OpenAI API key:
   - Get an API key from [OpenAI](https://platform.openai.com/api-keys)
   - Either enter it in the app's sidebar, or create a `.env` file:
```bash
OPENAI_API_KEY=your_api_key_here
```

## 🎯 Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser and go to `http://localhost:8501`

3. Configure your OpenAI API key in the sidebar

4. Choose your input type and paste your research content

5. Select presentation settings (type, slide count, template)

6. Click "Generate Presentation" and wait for AI magic!

## 📋 Presentation Types

- **Lab Meeting**: 10 slides, focus on methods and results
- **Conference Talk**: 20 slides, emphasize novelty and impact  
- **Thesis Defense**: 35 slides, detailed methodology
- **Lecture**: 15 slides, educational context

## 🔧 Requirements

- Python 3.9+
- OpenAI API key
- See `requirements.txt` for full dependencies

## 🚀 Deploy to Streamlit Cloud

This app is ready for deployment on [Streamlit Community Cloud](https://streamlit.io/cloud). Just connect your GitHub repository!

## 📝 License

MIT License - feel free to use and modify for your research needs!

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests.

---

Made with ❤️ for researchers 
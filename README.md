---
tags:
- gradio-theme
title: amethyst
colorFrom: gray
colorTo: green
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: apache-2.0
---
# Nutrition Assistant Chatbot

A multilingual nutrition assistant chatbot built with Gradio and OpenAI's GPT-3.5. The chatbot provides personalized nutrition advice, meal planning, and dietary recommendations based on user profiles.

## Features

- 🌍 Multilingual support (English and French)
- 👤 Personalized user profiles
- 🥗 Meal planning and suggestions
- 📊 Nutritional information and calculations
- 💪 Exercise and diet tips
- 🎯 Custom nutrition goals tracking
- 🌙 Dark/Light mode toggle

## Requirements

- Python 3.8+
- Gradio 4.44.0+
- OpenAI API key
- Other dependencies listed in requirements.txt

## Environment Variables

Create a `.env` file with:
```
OPENAI_API_KEY=your_api_key_here
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your OpenAI API key in `.env`

3. Run the app:
```bash
python app.py
```

## Usage

1. Enter your personal information (name, age, weight, height)
2. Select dietary preferences
3. Set nutrition goals
4. Use quick actions or chat with the bot for personalized advice

## License

MIT License

## Acknowledgments

- Built with [Gradio](https://gradio.app/)
- Themed with custom green color palette
- Icons from various emoji sets
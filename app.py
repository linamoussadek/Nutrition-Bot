import time 
import os
import json
from dotenv import load_dotenv
import openai
from typing import List
import gradio as gr
from gradio.themes.utils.theme_dropdown import create_theme_dropdown
from gradio.themes import Base
import asyncio

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

if not openai.api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

# Load translations
with open('translations.json', 'r', encoding='utf-8') as f:
    translations = json.load(f)

# Initialize current language
current_lang = "en"

def get_text(key: str) -> str:
    """Get translated text for a given key (dot-separated for nested keys)"""
    keys = key.split('.')
    value = translations[current_lang]
    for k in keys:
        value = value[k]
    return value

class NutritionBot:
    def __init__(self):
        self.user_data = {}
        self.conversation_history = []
        self.system_prompt = """You are a professional nutrition assistant with expertise in dietary planning and nutritional science. 
        Your role is to provide personalized, evidence-based nutrition advice while adhering to these guidelines:

        1. ONLY answer questions related to nutrition, diet, food, and healthy eating habits
        2. If asked about non-nutrition topics, politely redirect the conversation to nutrition-related topics
        3. Base all advice on scientific evidence and established nutritional guidelines
        4. Consider the user's complete profile (age, weight, dietary preferences, goals) when providing advice
        5. Be mindful of dietary restrictions and preferences
        6. Provide practical, actionable advice that's easy to implement
        7. Include specific food suggestions and meal ideas when relevant
        8. Explain the nutritional benefits of recommended foods
        9. Offer alternatives when suggesting foods that might not fit dietary preferences
        10. When discussing calories or nutrients, provide context for why they're important

        Safety Guidelines:
        - Acknowledge when a question requires professional medical advice
        - Don't make extreme dietary recommendations
        - Consider potential allergies and intolerances
        - Promote balanced, sustainable eating habits
        - Discourage harmful eating behaviors or extreme diets

        Remember to maintain a supportive and encouraging tone while providing accurate, science-based information."""
    
    def update_user_data(self, name: str, age: int, weight: float, height: float, dietary_prefs: List[str], 
                        calories: int = None, protein: int = None, water: float = None):
        self.user_data = {
            "name": name,
            "age": age,
            "weight": weight,
            "height": height,
            "bmi": round(weight / ((height/100) ** 2), 1) if weight and height else None,
            "dietary_preferences": dietary_prefs,
            "calorie_target": calories,
            "protein_target": protein,
            "water_target": water
        }
        
        bmr = self._calculate_bmr()
        tdee = self._calculate_tdee()
        greeting = f"👋 Hello {name}! "
        assessment = self._generate_health_assessment(bmr, tdee, calories, protein, water)
        user_context = f"""
        User Profile:
        - Name: {name}
        - Age: {age} years
        - Weight: {weight}kg
        - Height: {height}cm
        - BMI: {self.user_data['bmi']} (calculated)
        - Dietary Preferences: {', '.join(dietary_prefs) if dietary_prefs else 'None specified'}
        - Daily Targets: {calories}kcal, {protein}g protein, {water}L water
        - Estimated BMR: {bmr:.0f}kcal
        - Estimated TDEE: {tdee:.0f}kcal
        
        Health Status:
        - BMI Category: {self._get_bmi_category()}
        - Protein Needs: {self._calculate_protein_needs():.0f}g
        - Water Needs: {self._calculate_water_needs():.1f}L
        
        Provide personalized nutrition advice based on this profile. Consider:
        1. The user's BMI category and health status
        2. Their specific dietary preferences and restrictions
        3. Their calculated nutritional needs
        4. Age-appropriate recommendations
        5. Practical meal suggestions that fit their calorie targets
        """
        
        self.conversation_history = [
            {"role": "system", "content": self.system_prompt + user_context},
            {"role": "assistant", "content": greeting + assessment}
        ]

    def _calculate_bmr(self) -> float:
        if not all([self.user_data.get('weight'), self.user_data.get('height'), self.user_data.get('age')]):
            return 0
        weight = self.user_data['weight']
        height = self.user_data['height']
        age = self.user_data['age']
        return (10 * weight) + (6.25 * height) - (5 * age) + 5

    def _calculate_tdee(self) -> float:
        bmr = self._calculate_bmr()
        return bmr * 1.55

    def _get_bmi_category(self) -> str:
        bmi = self.user_data.get('bmi')
        if not bmi:
            return "Not available"
        if bmi < 18.5:
            return "Underweight"
        elif 18.5 <= bmi < 25:
            return "Normal weight"
        elif 25 <= bmi < 30:
            return "Overweight"
        else:
            return "Obese"

    def _calculate_protein_needs(self) -> float:
        if not self.user_data.get('weight'):
            return 0
        return self.user_data['weight'] * 1.6

    def _calculate_water_needs(self) -> float:
        if not self.user_data.get('weight'):
            return 0
        return self.user_data['weight'] * 0.033

    def _generate_health_assessment(self, bmr: float, tdee: float, calories: int, protein: int, water: float) -> str:
        assessment_parts = []
        bmi_category = self._get_bmi_category()
        if bmi_category != "Not available":
            assessment_parts.append(f"Based on your BMI of {self.user_data['bmi']}, you are in the {bmi_category.lower()} category.")
        if calories:
            calorie_diff = abs(calories - tdee)
            calorie_diff_percent = (calorie_diff / tdee) * 100
            if calorie_diff_percent > 30:
                assessment_parts.append(
                    f"⚠️ Your calorie target of {calories}kcal is significantly different from your estimated daily needs ({tdee:.0f}kcal). This might be unsustainable in the long term. Consider adjusting your target."
                )
            elif calorie_diff_percent > 15:
                assessment_parts.append(
                    f"Your calorie target of {calories}kcal is moderately different from your estimated daily needs ({tdee:.0f}kcal). Make sure this aligns with your health goals."
                )
            else:
                assessment_parts.append(
                    f"Your calorie target of {calories}kcal is well-aligned with your estimated daily needs ({tdee:.0f}kcal)."
                )
        if protein:
            protein_needs = self._calculate_protein_needs()
            protein_diff = abs(protein - protein_needs)
            protein_diff_percent = (protein_diff / protein_needs) * 100
            if protein_diff_percent > 50:
                assessment_parts.append(
                    f"⚠️ Your protein target of {protein}g is significantly different from recommended needs ({protein_needs:.0f}g). This might not be optimal for your health goals."
                )
            elif protein_diff_percent > 25:
                assessment_parts.append(
                    f"Your protein target of {protein}g is moderately different from recommended needs ({protein_needs:.0f}g). Consider adjusting based on your activity level."
                )
            else:
                assessment_parts.append(
                    f"Your protein target of {protein}g aligns well with recommended needs ({protein_needs:.0f}g)."
                )
        if water:
            water_needs = self._calculate_water_needs()
            water_diff = abs(water - water_needs)
            water_diff_percent = (water_diff / water_needs) * 100
            if water_diff_percent > 30:
                assessment_parts.append(
                    f"⚠️ Your water intake target of {water}L is significantly different from recommended needs ({water_needs:.1f}L). This might affect your hydration status."
                )
            elif water_diff_percent > 15:
                assessment_parts.append(
                    f"Your water intake target of {water}L is moderately different from recommended needs ({water_needs:.1f}L). Consider adjusting based on your activity level and climate."
                )
            else:
                assessment_parts.append(
                    f"Your water intake target of {water}L aligns well with recommended needs ({water_needs:.1f}L)."
                )
        if self.user_data.get('dietary_preferences'):
            prefs = self.user_data['dietary_preferences']
            if len(prefs) > 3:
                assessment_parts.append(
                    "⚠️ You have multiple dietary restrictions. Make sure you're getting all necessary nutrients. Consider consulting a nutritionist for a detailed meal plan."
                )
            else:
                assessment_parts.append(
                    f"Your dietary preferences ({', '.join(prefs)}) have been noted. I'll provide recommendations that align with these preferences."
                )
        if assessment_parts:
            return "\n\n".join(assessment_parts)
        return "I've noted your information and will provide personalized nutrition advice based on your profile."

    def is_nutrition_related(self, query: str) -> bool:
        nutrition_keywords = [
            'food', 'diet', 'nutrition', 'eat', 'meal', 'breakfast', 'lunch', 'dinner', 'snack',
            'recipe', 'cooking', 'cook', 'bake', 'baking', 'kitchen', 'restaurant', 'cafe',
            'calorie', 'protein', 'carb', 'carbohydrate', 'fat', 'fiber', 'fibre', 'vitamin',
            'mineral', 'nutrient', 'supplement', 'omega', 'antioxidant', 'mineral',
            'vegetable', 'fruit', 'meat', 'fish', 'seafood', 'dairy', 'grain', 'cereal',
            'legume', 'bean', 'nut', 'seed', 'spice', 'herb', 'oil', 'sauce', 'dressing',
            'healthy', 'health', 'wellness', 'weight', 'fitness', 'exercise', 'workout',
            'metabolism', 'digestion', 'energy', 'tired', 'fatigue', 'sleep', 'stress',
            'vegetarian', 'vegan', 'keto', 'paleo', 'gluten', 'dairy', 'allergy',
            'intolerance', 'organic', 'natural', 'processed', 'whole food',
            'should i', 'can i', 'what should', 'how much', 'how many', 'recommend',
            'suggestion', 'advice', 'help', 'guide', 'plan', 'schedule', 'routine',
            'diabetes', 'heart', 'blood pressure', 'cholesterol', 'digestive',
            'gut', 'immune', 'bone', 'muscle', 'joint', 'skin', 'hair'
        ]
        query_lower = query.lower()
        if any(keyword in query_lower for keyword in nutrition_keywords):
            return True
        question_patterns = [
            'what', 'how', 'why', 'when', 'where', 'which', 'should', 'can', 'could',
            'would', 'do', 'does', 'is', 'are', 'was', 'were', 'have', 'has', 'had'
        ]
        if any(query_lower.startswith(pattern) for pattern in question_patterns):
            return True
        health_adjectives = ['healthy', 'unhealthy', 'good', 'bad', 'better', 'best', 'worse', 'worst']
        if any(adj in query_lower for adj in health_adjectives):
            return True
        return False

    async def get_response(self, message: str) -> str:
        if not self.is_nutrition_related(message):
            return "I'm your nutrition assistant, so I can only help with questions about food, diet, and nutrition. Could you please ask me something related to nutrition or healthy eating?"
        greeting_parts = []
        if self.user_data.get('height') or self.user_data.get('weight') or self.user_data.get('age'):
            greeting_parts.append("I see that")
            info_parts = []
            if self.user_data.get('height'):
                info_parts.append(f"your height is {self.user_data['height']}cm")
            if self.user_data.get('weight'):
                info_parts.append(f"your weight is {self.user_data['weight']}kg")
            if self.user_data.get('age'):
                info_parts.append(f"you're {self.user_data['age']} years old")
            greeting_parts.append(", ".join(info_parts))
        if self.user_data.get('dietary_preferences'):
            greeting_parts.append(f"and you follow a {', '.join(self.user_data['dietary_preferences'])} diet")
        greeting = " ".join(greeting_parts) + ".\n\n"
        self.conversation_history.append({"role": "user", "content": message})
        max_retries = 3
        retry_delay = 1
        for attempt in range(max_retries):
            try:
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self.conversation_history,
                    temperature=0.7,
                    max_tokens=500,
                    top_p=0.9,
                    frequency_penalty=0.3,
                    presence_penalty=0.3,
                    timeout=30
                )
                bot_response = response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": bot_response})
                return greeting + bot_response
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                return "I'm experiencing high demand right now. Please try again in a few moments."
            except openai.APIError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                return f"I apologize, but I encountered an API error. Please try again later. Error: {str(e)}"
            except Exception as e:
                return f"I apologize, but I encountered an unexpected error. Please try again. Error: {str(e)}"

nutrition_bot = NutritionBot()

class AmethystTheme(Base):
    def __init__(self):
        super().__init__(
            primary_hue="green",
            secondary_hue="emerald",
            neutral_hue="gray",         
        )
        self.name = "nutrition_theme"
        self.color_accent = "#4CAF50"
        self.color_accent_soft = "rgba(76, 175, 80, 0.2)"
        self.background_fill_primary = "#FFFFFF"
        self.background_fill_secondary = "#F1F8E9"
        self.border_color_primary = "#81C784"
        self.block_title_text_color = "#2E7D32"
        self.block_border_color = "#81C784"
        self.button_primary_background_fill = "#4CAF50"
        self.button_primary_background_fill_hover = "#43A047"
        self.button_secondary_background_fill = "#F1F8E9"
        self.button_secondary_border_color = "#81C784"
        self.button_secondary_text_color = "#2E7D32"
        self.dark_mode_colors = {
            "background_fill_primary": "#1B2A1B",
            "background_fill_secondary": "#243024",
            "block_background_fill": "#1B2A1B",
            "block_border_color": "#4CAF50",
            "block_label_text_color": "#81C784",
            "block_title_text_color": "#A5D6A7",
            "body_background_fill": "linear-gradient(135deg, #162316 0%, #1B2A1B 100%)",
            "body_text_color": "#E8F5E9",
            "button_primary_background_fill": "#4CAF50",
            "button_primary_text_color": "#FFFFFF",
            "button_secondary_background_fill": "#243024",
            "button_secondary_border_color": "#4CAF50",
            "button_secondary_text_color": "#A5D6A7",
            "color_accent": "#81C784",
            "color_accent_soft": "rgba(129, 199, 132, 0.2)",
            "input_background_fill": "#243024",
            "input_border_color": "#4CAF50",
            "input_text_color": "#E8F5E9",
            "checkbox_background_color": "#243024",
            "checkbox_border_color": "#4CAF50",
            "slider_color": "#4CAF50",
            "block_label_background_fill": "rgba(76, 175, 80, 0.1)"
        }
        self.spacing_md = "12px"
        self.spacing_lg = "16px"
        self.spacing_xl = "20px"
        self.spacing_xxl = "32px"
        self.radius_lg = "12px"
        self.shadow_drop = "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)"
        self.text_md = "15px"
        self.text_lg = "18px"
        self.text_xl = "24px"
        for key, value in self.dark_mode_colors.items():
            setattr(self, key + "_dark", value)

css = """
.nutrition-header { 
    text-align: center;
    margin-bottom: 24px;
    padding: 24px;
    border-radius: 12px;
    background: rgba(76, 175, 80, 0.1);
}
.nutrition-header h1 { 
    margin-bottom: 16px;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
}
.user-info {
    padding: 20px;
    border-radius: 12px;
    background: rgba(76, 175, 80, 0.05);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border: 1px solid rgba(76, 175, 80, 0.2);
}
.dark .user-info {
    background: rgba(76, 175, 80, 0.1);
    border-color: rgba(76, 175, 80, 0.3);
}
.chat-container {
    border-radius: 12px;
    overflow: hidden;
}
.quick-actions {
    background: rgba(76, 175, 80, 0.05);
    padding: 16px;
    border-radius: 12px;
    border: 1px solid rgba(76, 175, 80, 0.2);
}
.dark .quick-actions {
    background: rgba(76, 175, 80, 0.1);
    border-color: rgba(76, 175, 80, 0.3);
}
.equal-width {
    flex: 1;
    min-width: 0;
    padding: 0 8px;
}
.equal-width input {
    width: 100%;
}
"""

with gr.Blocks(theme=AmethystTheme(), css=css) as demo:
    with gr.Row(equal_height=True):
        with gr.Column(scale=1):
            toggle_dark = gr.Button(get_text("theme.toggle_dark"), size="sm")
        with gr.Column(scale=1):
            language = gr.Dropdown(
                choices=["en", "fr"],
                value="en",
                label="Language",
                info="Select your preferred language"
            )
            lang_state = gr.State("en")  # Add language state
    with gr.Row(equal_height=True):
        with gr.Column(scale=10, elem_classes="nutrition-header"):
            header_md = gr.Markdown(
                f"""
                # 🥗 {get_text("title")}
                {get_text("welcome")}
                - 📋 {get_text("features.meal_planning")}
                - 🍎 {get_text("features.nutrition_info")}
                - 🥑 {get_text("features.dietary_recs")}
                - 💪 {get_text("features.eating_tips")}
                """
            )
    
    with gr.Column(elem_classes="user-info"):
        with gr.Row():
            with gr.Column(elem_classes="equal-width"):
                name = gr.Textbox(
                    label=f"👤 {get_text('user_info.name_label')}",
                    info=get_text("user_info.name_info"),
                    placeholder=get_text("user_info.name_placeholder"),
                    value="",
                    interactive=True,
                )
            with gr.Column(elem_classes="equal-width"):
                age = gr.Number(
                    label=f"🎂 {get_text('user_info.age_label')}",
                    info=get_text("user_info.age_info"),
                    value=25,
                    minimum=0,
                    maximum=120
                )
            with gr.Column(elem_classes="equal-width"):
                weight = gr.Number(
                    label=f"⚖️ {get_text('user_info.weight_label')}",
                    info=get_text("user_info.weight_info"),
                    value=70,
                    minimum=20,
                    maximum=300
                )
            with gr.Column(elem_classes="equal-width"):
                height = gr.Number(
                    label=f"📏 {get_text('user_info.height_label')}",
                    info=get_text("user_info.height_info"),
                    value=170,
                    minimum=100,
                    maximum=250
                )
        with gr.Row():
            dietary_prefs = gr.CheckboxGroup(
                ["🥬 Vegetarian", "🌱 Vegan", "🌾 Gluten-Free", "🥛 Dairy-Free", "🥑 Keto", "🍖 Paleo"],
                label=get_text("user_info.dietary_prefs_label"),
                info=get_text("user_info.dietary_prefs_info")
            )
    
    with gr.Row(equal_height=True):
        with gr.Column(variant="panel", scale=1):
            with gr.Column(elem_classes="quick-actions"):
                quick_actions_md = gr.Markdown(f"### ⚡ {get_text('quick_actions.title')}")
                quick_actions = gr.Radio(
                    [
                        "🍽️ " + get_text("quick_actions.actions.meal_suggestions"),
                        "📊 " + get_text("quick_actions.actions.daily_calories"),
                        "🔍 " + get_text("quick_actions.actions.food_nutrition"),
                        "🏃‍♂️ " + get_text("quick_actions.actions.exercise_tips"),
                        "📅 " + get_text("quick_actions.actions.weekly_menu")
                    ],
                    label=get_text("quick_actions.common_tasks"),
                    info=get_text("quick_actions.common_tasks_info")
                )
                nutrition_goals_acc = gr.Accordion(get_text("quick_actions.nutrition_goals"), open=False)
                with nutrition_goals_acc:
                    gr.Markdown(get_text("quick_actions.nutrition_goals_info"))
                    calories = gr.Number(label="🔥 Daily Calorie Target", value=2000)
                    protein = gr.Number(label="🥩 Protein Goal (g)", value=150)
                    water = gr.Number(label="💧 Water Intake Goal (L)", value=2.5)
        with gr.Column(variant="panel", scale=2):
            with gr.Column(elem_classes="chat-container"):
                chatbot = gr.Chatbot(
                    [{"role": "assistant", "content": get_text("chat.welcome_message")}],
                    label=get_text("chat.label"),
                    height=500,
                    type="messages"
                )
                with gr.Row():
                    msg = gr.Textbox(
                        label=get_text("chat.label"),
                        placeholder=get_text("chat.message_placeholder"),
                        show_label=False,
                        container=False,
                        scale=7
                    )
                    submit_btn = gr.Button("📤 " + get_text("chat.send_button"), variant="primary", scale=2)
                with gr.Row():
                    clear_btn = gr.Button("🗑️ " + get_text("chat.clear_button"), variant="secondary", size="sm", scale=1)

    def update_profile(*args):
        nutrition_bot.update_user_data(*args)
        return f"Profile updated for {args[0]}"

    profile_inputs = [name, age, weight, height, dietary_prefs, calories, protein, water]
    for input_component in profile_inputs:
        input_component.change(
            update_profile,
            inputs=profile_inputs,
            outputs=gr.Textbox(visible=False)
        )

    def handle_quick_action(action: str) -> str:
        action_prompts = {
            "🍽️ " + get_text("quick_actions.actions.meal_suggestions"): "Can you suggest some healthy meals that fit my dietary preferences and calorie goals?",
            "📊 " + get_text("quick_actions.actions.daily_calories"): "Based on my age, weight, and activity level, how many calories should I consume daily?",
            "🔍 " + get_text("quick_actions.actions.food_nutrition"): "Can you tell me about the nutritional content of common foods in my diet?",
            "🏃‍♂️ " + get_text("quick_actions.actions.exercise_tips"): "What types of exercise would complement my nutrition goals?",
            "📅 " + get_text("quick_actions.actions.weekly_menu"): "Can you help me create a weekly meal plan that meets my nutritional goals?"
        }
        return action_prompts.get(action, "")

    async def respond(message, history):
        bot_response = await nutrition_bot.get_response(message)
        return history + [{"role": "user", "content": message}, {"role": "assistant", "content": bot_response}]

    msg.submit(respond, [msg, chatbot], [chatbot]).then(lambda: "", None, [msg])
    submit_btn.click(respond, [msg, chatbot], [chatbot]).then(lambda: "", None, [msg])
    clear_btn.click(lambda: None, None, chatbot)
    quick_actions.change(handle_quick_action, quick_actions, msg)
    toggle_dark.click(None, js="() => {document.body.classList.toggle('dark');}")

    # Language change callback: update only updateable properties
    def update_language(lang: str):
        global current_lang
        current_lang = lang

        # Create the quick actions choices list
        quick_actions_choices = [
            "🍽️ " + get_text("quick_actions.actions.meal_suggestions"),
            "📊 " + get_text("quick_actions.actions.daily_calories"),
            "🔍 " + get_text("quick_actions.actions.food_nutrition"),
            "🏃‍♂️ " + get_text("quick_actions.actions.exercise_tips"),
            "📅 " + get_text("quick_actions.actions.weekly_menu")
        ]

        return (
            f"👤 {get_text('user_info.name_label')}",  # name label
            get_text("user_info.name_info"),            # name info
            get_text("user_info.name_placeholder"),     # name placeholder
            f"🎂 {get_text('user_info.age_label')}",    # age label
            get_text("user_info.age_info"),             # age info
            f"⚖️ {get_text('user_info.weight_label')}", # weight label
            get_text("user_info.weight_info"),          # weight info
            f"📏 {get_text('user_info.height_label')}", # height label
            get_text("user_info.height_info"),          # height info
            get_text("user_info.dietary_prefs_label"),  # dietary prefs label
            get_text("user_info.dietary_prefs_info"),   # dietary prefs info
            gr.update(choices=quick_actions_choices, label=get_text("quick_actions.common_tasks"), info=get_text("quick_actions.common_tasks_info")),  # quick actions radio
            gr.update(label=get_text("quick_actions.nutrition_goals")),  # nutrition goals accordion
            gr.update(value=[{"role": "assistant", "content": get_text("chat.welcome_message")}]),  # chatbot
            get_text("chat.message_placeholder"),        # message placeholder
            "📤 " + get_text("chat.send_button"),        # send button
            "🗑️ " + get_text("chat.clear_button"),       # clear button
            get_text("theme.toggle_dark")                # toggle dark button
        )

    language.change(
        update_language,
        inputs=[language],
        outputs=[
            name,                    # name textbox
            name,                    # name info
            name,                    # name placeholder
            age,                     # age number
            age,                     # age info
            weight,                  # weight number
            weight,                  # weight info
            height,                  # height number
            height,                  # height info
            dietary_prefs,           # dietary prefs checkbox group
            dietary_prefs,           # dietary prefs info
            quick_actions,           # quick actions radio
            nutrition_goals_acc,     # nutrition goals accordion
            chatbot,                 # chatbot
            msg,                     # message textbox
            submit_btn,              # submit button
            clear_btn,               # clear button
            toggle_dark              # toggle dark button
        ]
    ).then(
        lambda lang: lang,
        inputs=[language],
        outputs=[lang_state]
    )

if __name__ == "__main__":
    demo.queue().launch()

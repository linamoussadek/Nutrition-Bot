import time
import os
from dotenv import load_dotenv
import openai
from typing import Dict, List
import gradio as gr
from gradio.themes.utils.theme_dropdown import create_theme_dropdown
from gradio.themes import Base
import asyncio

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

if not openai.api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

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
        """Update user profile data"""
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
        
        # Calculate additional health metrics
        bmr = self._calculate_bmr()
        tdee = self._calculate_tdee()
        
        # Generate personalized greeting and assessment
        greeting = f"👋 Hello {name}! "
        assessment = self._generate_health_assessment(bmr, tdee, calories, protein, water)
        
        # Update system prompt with detailed user context
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
        
        # Update conversation history with greeting and assessment
        self.conversation_history = [
            {"role": "system", "content": self.system_prompt + user_context},
            {"role": "assistant", "content": greeting + assessment}
        ]

    def _calculate_bmr(self) -> float:
        """Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation"""
        if not all([self.user_data.get('weight'), self.user_data.get('height'), self.user_data.get('age')]):
            return 0
        weight = self.user_data['weight']
        height = self.user_data['height']
        age = self.user_data['age']
        return (10 * weight) + (6.25 * height) - (5 * age) + 5

    def _calculate_tdee(self) -> float:
        """Calculate Total Daily Energy Expenditure (using moderate activity factor)"""
        bmr = self._calculate_bmr()
        return bmr * 1.55  # Moderate activity factor

    def _get_bmi_category(self) -> str:
        """Get BMI category based on calculated BMI"""
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
        """Calculate protein needs based on weight and activity level"""
        if not self.user_data.get('weight'):
            return 0
        weight = self.user_data['weight']
        return weight * 1.6  # Moderate activity level multiplier

    def _calculate_water_needs(self) -> float:
        """Calculate daily water needs based on weight"""
        if not self.user_data.get('weight'):
            return 0
        weight = self.user_data['weight']
        return weight * 0.033  # 33ml per kg of body weight

    def _generate_health_assessment(self, bmr: float, tdee: float, calories: int, protein: int, water: float) -> str:
        """Generate a personalized health assessment based on user's metrics"""
        assessment_parts = []
        
        # BMI Assessment
        bmi_category = self._get_bmi_category()
        if bmi_category != "Not available":
            assessment_parts.append(f"Based on your BMI of {self.user_data['bmi']}, you are in the {bmi_category.lower()} category.")
        
        # Calorie Assessment
        if calories:
            calorie_diff = abs(calories - tdee)
            calorie_diff_percent = (calorie_diff / tdee) * 100
            
            if calorie_diff_percent > 30:
                assessment_parts.append(
                    f"⚠️ Your calorie target of {calories}kcal is significantly different from your estimated daily needs ({tdee:.0f}kcal). "
                    "This might be unsustainable in the long term. Consider adjusting your target."
                )
            elif calorie_diff_percent > 15:
                assessment_parts.append(
                    f"Your calorie target of {calories}kcal is moderately different from your estimated daily needs ({tdee:.0f}kcal). "
                    "Make sure this aligns with your health goals."
                )
            else:
                assessment_parts.append(
                    f"Your calorie target of {calories}kcal is well-aligned with your estimated daily needs ({tdee:.0f}kcal)."
                )
        
        # Protein Assessment
        if protein:
            protein_needs = self._calculate_protein_needs()
            protein_diff = abs(protein - protein_needs)
            protein_diff_percent = (protein_diff / protein_needs) * 100
            
            if protein_diff_percent > 50:
                assessment_parts.append(
                    f"⚠️ Your protein target of {protein}g is significantly different from recommended needs ({protein_needs:.0f}g). "
                    "This might not be optimal for your health goals."
                )
            elif protein_diff_percent > 25:
                assessment_parts.append(
                    f"Your protein target of {protein}g is moderately different from recommended needs ({protein_needs:.0f}g). "
                    "Consider adjusting based on your activity level."
                )
            else:
                assessment_parts.append(
                    f"Your protein target of {protein}g aligns well with recommended needs ({protein_needs:.0f}g)."
                )
        
        # Water Assessment
        if water:
            water_needs = self._calculate_water_needs()
            water_diff = abs(water - water_needs)
            water_diff_percent = (water_diff / water_needs) * 100
            
            if water_diff_percent > 30:
                assessment_parts.append(
                    f"⚠️ Your water intake target of {water}L is significantly different from recommended needs ({water_needs:.1f}L). "
                    "This might affect your hydration status."
                )
            elif water_diff_percent > 15:
                assessment_parts.append(
                    f"Your water intake target of {water}L is moderately different from recommended needs ({water_needs:.1f}L). "
                    "Consider adjusting based on your activity level and climate."
                )
            else:
                assessment_parts.append(
                    f"Your water intake target of {water}L aligns well with recommended needs ({water_needs:.1f}L)."
                )
        
        # Dietary Preferences Assessment
        if self.user_data.get('dietary_preferences'):
            prefs = self.user_data['dietary_preferences']
            if len(prefs) > 3:
                assessment_parts.append(
                    "⚠️ You have multiple dietary restrictions. Make sure you're getting all necessary nutrients. "
                    "Consider consulting a nutritionist for a detailed meal plan."
                )
            else:
                assessment_parts.append(
                    f"Your dietary preferences ({', '.join(prefs)}) have been noted. "
                    "I'll provide recommendations that align with these preferences."
                )
        
        # Combine all assessments
        if assessment_parts:
            return "\n\n".join(assessment_parts)
        return "I've noted your information and will provide personalized nutrition advice based on your profile."

    def is_nutrition_related(self, query: str) -> bool:
        """Check if the query is nutrition-related"""
        nutrition_keywords = [
            # Food and meals
            'food', 'diet', 'nutrition', 'eat', 'meal', 'breakfast', 'lunch', 'dinner', 'snack',
            'recipe', 'cooking', 'cook', 'bake', 'baking', 'kitchen', 'restaurant', 'cafe',
            
            # Nutrients and components
            'calorie', 'protein', 'carb', 'carbohydrate', 'fat', 'fiber', 'fibre', 'vitamin',
            'mineral', 'nutrient', 'supplement', 'omega', 'antioxidant', 'mineral',
            
            # Food groups
            'vegetable', 'fruit', 'meat', 'fish', 'seafood', 'dairy', 'grain', 'cereal',
            'legume', 'bean', 'nut', 'seed', 'spice', 'herb', 'oil', 'sauce', 'dressing',
            
            # Health and wellness
            'healthy', 'health', 'wellness', 'weight', 'fitness', 'exercise', 'workout',
            'metabolism', 'digestion', 'energy', 'tired', 'fatigue', 'sleep', 'stress',
            
            # Dietary preferences and restrictions
            'vegetarian', 'vegan', 'keto', 'paleo', 'gluten', 'dairy', 'allergy',
            'intolerance', 'organic', 'natural', 'processed', 'whole food',
            
            # Portions and measurements
            'portion', 'serving', 'size', 'amount', 'quantity', 'measure', 'cup', 'gram',
            'ounce', 'pound', 'kilogram', 'liter', 'milliliter',
            
            # Common nutrition questions
            'should i', 'can i', 'what should', 'how much', 'how many', 'recommend',
            'suggestion', 'advice', 'help', 'guide', 'plan', 'schedule', 'routine',
            
            # Health conditions
            'diabetes', 'heart', 'blood pressure', 'cholesterol', 'digestive',
            'gut', 'immune', 'bone', 'muscle', 'joint', 'skin', 'hair'
        ]
        
        # Convert query to lowercase for case-insensitive matching
        query_lower = query.lower()
        
        # Check for direct keyword matches
        if any(keyword in query_lower for keyword in nutrition_keywords):
            return True
            
        # Check for question patterns
        question_patterns = [
            'what', 'how', 'why', 'when', 'where', 'which', 'should', 'can', 'could',
            'would', 'do', 'does', 'is', 'are', 'was', 'were', 'have', 'has', 'had'
        ]
        
        # If the query starts with a question word, it's likely a nutrition question
        if any(query_lower.startswith(pattern) for pattern in question_patterns):
            return True
            
        # Check for health-related adjectives
        health_adjectives = ['healthy', 'unhealthy', 'good', 'bad', 'better', 'best', 'worse', 'worst']
        if any(adj in query_lower for adj in health_adjectives):
            return True
            
        return False

    async def get_response(self, message: str) -> str:
        """Get response from ChatGPT with nutrition focus"""
        if not self.is_nutrition_related(message):
            return "I'm your nutrition assistant, so I can only help with questions about food, diet, and nutrition. Could you please ask me something related to nutrition or healthy eating?"

        # Generate personalized greeting with user info
        greeting_parts = []
        
        # Add user information in a natural way
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

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})
        
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Get response from ChatGPT with optimized parameters
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self.conversation_history,
                    temperature=0.7,  # Balanced between creativity and consistency
                    max_tokens=500,   # Limit response length
                    top_p=0.9,        # Nucleus sampling for better quality
                    frequency_penalty=0.3,  # Reduce repetition
                    presence_penalty=0.3,   # Encourage new topics
                    timeout=30  # 30 second timeout
                )
                
                # Extract and store response
                bot_response = response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": bot_response})
                
                # Combine greeting with response
                return greeting + bot_response
                
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                return "I'm experiencing high demand right now. Please try again in a few moments."
            
            except openai.APIError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                return f"I apologize, but I encountered an API error. Please try again later. Error: {str(e)}"
            
            except Exception as e:
                return f"I apologize, but I encountered an unexpected error. Please try again. Error: {str(e)}"

# Initialize the nutrition bot
nutrition_bot = NutritionBot()

# Create a custom theme class
class AmethystTheme(Base):
    def __init__(self):
        super().__init__(
            primary_hue="green",
            secondary_hue="emerald",
            neutral_hue="gray",         
        )
        self.name = "nutrition_theme"
        
        # Light mode colors
        self.color_accent = "#4CAF50"  # Fresh green
        self.color_accent_soft = "rgba(76, 175, 80, 0.2)"  # Soft green
        self.background_fill_primary = "#FFFFFF"
        self.background_fill_secondary = "#F1F8E9"  # Very light green
        self.border_color_primary = "#81C784"  # Medium green
        self.block_title_text_color = "#2E7D32"  # Dark green
        self.block_border_color = "#81C784"
        self.button_primary_background_fill = "#4CAF50"
        self.button_primary_background_fill_hover = "#43A047"
        self.button_secondary_background_fill = "#F1F8E9"
        self.button_secondary_border_color = "#81C784"
        self.button_secondary_text_color = "#2E7D32"
        
        # Dark mode colors
        self.dark_mode_colors = {
            "background_fill_primary": "#1B2A1B",  # Dark forest green
            "background_fill_secondary": "#243024",  # Slightly lighter forest green
            "block_background_fill": "#1B2A1B",
            "block_border_color": "#4CAF50",
            "block_label_text_color": "#81C784",
            "block_title_text_color": "#A5D6A7",  # Light green for contrast
            "body_background_fill": "linear-gradient(135deg, #162316 0%, #1B2A1B 100%)",
            "body_text_color": "#E8F5E9",  # Very light green text
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
        
        # Add some spacing and sizing configurations
        self.spacing_md = "12px"  # Increased from 6px
        self.spacing_lg = "16px"  # Increased from 8px
        self.spacing_xl = "20px"  # Increased from 10px
        self.spacing_xxl = "32px" # Increased from 16px
        
        self.radius_lg = "12px"   # Increased from 8px
        self.shadow_drop = "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)"
        
        # Increase text sizes slightly
        self.text_md = "15px"     # Increased from 14px
        self.text_lg = "18px"     # Increased from 16px
        self.text_xl = "24px"     # Increased from 22px
        
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

dropdown, js = create_theme_dropdown()

# Use our custom theme
with gr.Blocks(theme=AmethystTheme(), css=css) as demo:
    with gr.Row(equal_height=True):
        with gr.Column(scale=10):
            with gr.Column(scale=1):
                toggle_dark = gr.Button("🌙 Toggle Dark Mode", size="sm")
            with gr.Column(elem_classes="nutrition-header"):
                gr.Markdown(
                    """
                    # 🥗 Nutrition Assistant
                    Welcome to your personal nutrition assistant! I can help you with:
                    - 📋 Meal planning and recipe suggestions
                    - 🍎 Nutritional information about foods
                    - 🥑 Dietary recommendations
                    - 💪 Healthy eating tips
                    """
                )
        

    with gr.Column(elem_classes="user-info"):
        with gr.Row():
            with gr.Column(elem_classes="equal-width"):
                name = gr.Textbox(
                    label="👤 Your Name",
                    info="Let me personalize recommendations for you",
                    placeholder="John Smith",
                    value="",
                    interactive=True,
                )
            with gr.Column(elem_classes="equal-width"):
                age = gr.Number(
                    label="🎂 Age",
                    info="Let me adjust recommendations based on your age group",
                    value=25,
                    minimum=0,
                    maximum=120
                )
            with gr.Column(elem_classes="equal-width"):
                weight = gr.Number(
                    label="⚖️ Weight (kg)",
                    info="Help me calculate your nutritional needs accurately",
                    value=70,
                    minimum=20,
                    maximum=300
                )
            with gr.Column(elem_classes="equal-width"):
                height = gr.Number(
                    label="📏 Height (cm)",
                    info="I'll use this to determine your ideal caloric intake",
                    value=170,
                    minimum=100,
                    maximum=250
                )
        
        with gr.Row():
            dietary_prefs = gr.CheckboxGroup(
                ["🥬 Vegetarian", "🌱 Vegan", "🌾 Gluten-Free", "🥛 Dairy-Free", "🥑 Keto", "🍖 Paleo"],
                label="Dietary Preferences",
                info="Select all that apply to receive tailored meal suggestions"
            )

    with gr.Row(equal_height=True):
        with gr.Column(variant="panel", scale=1):
            with gr.Column(elem_classes="quick-actions"):
                gr.Markdown("### ⚡ Quick Actions")
                quick_actions = gr.Radio(
                    [
                        "🍽️ Get meal suggestions",
                        "📊 Calculate daily calories",
                        "🔍 Check food nutrition facts",
                        "🏃‍♂️ Get exercise tips",
                        "📅 Plan weekly menu"
                    ],
                    label="Common Tasks",
                    info="Click any action to get started"
                )
                
                with gr.Accordion("🎯 Nutrition Goals", open=False):
                    gr.Markdown("Set your personal targets:")
                    calories = gr.Number(label="🔥 Daily Calorie Target", value=2000)
                    protein = gr.Number(label="🥩 Protein Goal (g)", value=150)
                    water = gr.Number(label="💧 Water Intake Goal (L)", value=2.5)
        with gr.Column(variant="panel", scale=2):
            with gr.Column(elem_classes="chat-container"):
                chatbot = gr.Chatbot(
                    [{"role": "assistant", "content": "👋 Hi! I'm your nutrition assistant. How can I help you today?"}],
                    label="Nutrition Chat",
                    height=500,
                    type="messages"
                )
                with gr.Row():
                    msg = gr.Textbox(
                        label="Your Message",
                        placeholder="Ask me anything about nutrition...",
                        show_label=False,
                        container=False,
                        scale=7
                    )
                    submit_btn = gr.Button("📤 Send", variant="primary", scale=2)
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary", size="sm", scale=1)

    # Update user profile when any input changes
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

    # Quick action handler
    def handle_quick_action(action: str) -> str:
        action_prompts = {
            "🍽️ Get meal suggestions": "Can you suggest some healthy meals that fit my dietary preferences and calorie goals?",
            "📊 Calculate daily calories": "Based on my age, weight, and activity level, how many calories should I consume daily?",
            "🔍 Check food nutrition facts": "Can you tell me about the nutritional content of common foods in my diet?",
            "🏃‍♂️ Get exercise tips": "What types of exercise would complement my nutrition goals?",
            "📅 Plan weekly menu": "Can you help me create a weekly meal plan that meets my nutritional goals?"
        }
        return action_prompts.get(action, "")

    # Enhanced response function using ChatGPT
    async def respond(message, history):
        bot_response = await nutrition_bot.get_response(message)
        return history + [{"role": "user", "content": message}, 
                         {"role": "assistant", "content": bot_response}]

    # Event handlers
    msg.submit(respond, [msg, chatbot], [chatbot]).then(lambda: "", None, [msg])
    submit_btn.click(respond, [msg, chatbot], [chatbot]).then(lambda: "", None, [msg])
    clear_btn.click(lambda: None, None, chatbot)
    quick_actions.change(handle_quick_action, quick_actions, msg)
    toggle_dark.click(None, js="() => {document.body.classList.toggle('dark');}")

if __name__ == "__main__":
    demo.queue().launch()
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
import os
import groq
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix

def modify_prompt_for_bulgarian(prompt):
    return prompt + "\n\nPlease provide the recipe in Bulgarian language only. All measurements, instructions, and descriptions should be in Bulgarian."

load_dotenv()

# Load the appropriate .env file
if os.getenv('FLASK_ENV') == 'production':
    load_dotenv('.env.production')
else:
    load_dotenv()

app = Flask(__name__)

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; img-src 'self' data:;"
    return response

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='404 - Page Not Found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='500 - Internal Server Error'), 500

# Rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize Groq client
client = groq.Groq(api_key=os.getenv('GROQ_API_KEY'))

# Support for proxy servers
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

INGREDIENTS = {
    'meat': [
        '🥩 Beef', '🍗 Chicken', '🐷 Pork', '🐟 Fish', '🦃 Turkey', '🦆 Duck',
        '🐑 Lamb', '🦐 Shrimp', '🦀 Crab', '🐙 Octopus', '🦑 Squid', '🐠 Salmon'
    ],
    'vegetables': [
        '🥕 Carrot', '🥦 Broccoli', '🍅 Tomato', '🥬 Lettuce', '🫑 Bell Pepper',
        '🧅 Onion', '🥒 Cucumber', '🍆 Eggplant', '🥔 Potato', '🍠 Sweet Potato',
        '🥗 Spinach', '🥬 Kale', '🌽 Corn', '🥜 Peanuts', '🫘 Beans', '🥜 Chickpeas',
        '🥦 Cauliflower', '🥬 Cabbage', '🍄 Mushroom', '🥝 Zucchini'
    ],
    'spices': [
        '🌶️ Chili', '🧄 Garlic', '🌿 Basil', '🌱 Oregano', '🍃 Thyme',
        '🧂 Salt', '⚫ Black Pepper', '🟡 Turmeric', '🟤 Cinnamon', '🟡 Ginger',
        '🟤 Cumin', '🟡 Curry Powder', '🔴 Paprika', '🟡 Saffron', '🌿 Rosemary',
        '🌿 Sage', '🌿 Mint', '🌶️ Cayenne', '⭐ Star Anise', '🟤 Nutmeg'
    ],
    'grains': [
        '🍚 Rice', '🍝 Pasta', '🥖 Bread', '🌽 Corn', '🥣 Quinoa',
        '🥯 Bagel', '🥨 Pretzel', '🥜 Oats', '🌾 Barley', '🌾 Rye',
        '🥖 Sourdough', '🍝 Noodles', '🌾 Couscous', '🌾 Buckwheat', '🌾 Millet'
    ],
    'dairy': [
        '🥛 Milk', '🧀 Cheese', '🧈 Butter', '🥛 Yogurt', '🥛 Cream',
        '🧀 Mozzarella', '🧀 Cheddar', '🧀 Parmesan', '🧀 Feta', '🥛 Sour Cream'
    ],
    'fruits': [
        '🍎 Apple', '🍌 Banana', '🍊 Orange', '🍇 Grapes', '🍓 Strawberry',
        '🫐 Blueberry', '🥝 Kiwi', '🍍 Pineapple', '🥭 Mango', '🍑 Peach',
        '🍐 Pear', '🍒 Cherry', '🥥 Coconut', '🫐 Raspberry', '🍇 Blackberry'
    ],
    'herbs': [
        '🌿 Parsley', '🌿 Cilantro', '🌿 Dill', '🌿 Chives', '🌿 Tarragon',
        '🌿 Lemongrass', '🌿 Bay Leaf', '🌿 Marjoram', '🌿 Fennel', '🌿 Lavender'
    ],
    'nuts_seeds': [
        '🥜 Almonds', '🥜 Walnuts', '🥜 Cashews', '🌰 Hazelnuts', '🥜 Pistachios',
        '🌱 Chia Seeds', '🌱 Flax Seeds', '🌱 Sunflower Seeds', '🌱 Pumpkin Seeds', '🥜 Pine Nuts'
    ],
    'condiments': [
        '🥫 Ketchup', '🟡 Mustard', '🥫 Mayo', '🫒 Olive Oil', '🥢 Soy Sauce',
        '🍯 Honey', '🧂 Vinegar', '🥫 Hot Sauce', '🥫 BBQ Sauce', '🥫 Worcestershire'
    ]
}

DIETARY_PREFERENCES = ['Vegetarian', 'Vegan', 'Gluten-Free', 'Keto', 'Low-Carb', 'Dairy-Free', 'Budget-Friendly']

@app.route('/')
def index():
    return render_template('index.html', 
                         ingredients=INGREDIENTS,
                         dietary_preferences=DIETARY_PREFERENCES)

@app.route('/set_language', methods=['POST'])
def set_language():
    lang = request.json.get('language')
    if lang in TRANSLATIONS:
        session['language'] = lang
        return jsonify({'status': 'success', 'translations': TRANSLATIONS[lang]})
    return jsonify({'status': 'error', 'message': 'Language not supported'})

@app.route('/generate_recipe', methods=['POST'])
def generate_recipe():
    data = request.json
    selected_ingredients = data.get('ingredients', [])
    dietary_prefs = data.get('dietary_preferences', [])
    
    is_budget = 'Budget-Friendly' in dietary_prefs
    budget_prompt = """
    Make this a budget-friendly recipe by:
    1. Using affordable ingredients
    2. Minimizing waste
    3. Using simple cooking methods
    4. Suggesting cheaper alternatives when possible
    """ if is_budget else ""

    prompt = f"""You are a professional nutritionist and chef AI. Generate a recipe using these ingredients: {', '.join(selected_ingredients)}. 
    Dietary preferences: {', '.join(dietary_prefs)}.
    {budget_prompt}
    
    IMPORTANT: Your response must be ONLY valid JSON, with no additional text before or after. Do not include markdown code blocks or any other formatting.
    Do not escape underscores in field names - use them as is.
    
    Return the recipe in this EXACT JSON format:
    {{
        "name": "Recipe Name",
        "prep_time": "XX minutes",
        "cooking_time": "XX minutes",
        "servings": "X servings",
        "ingredients": [
            "ingredient 1 with precise measurement in grams/milliliters",
            "ingredient 2 with precise measurement in grams/milliliters"
        ],
        "instructions": [
            "Step 1 instruction (use Celsius for temperatures)",
            "Step 2 instruction (use Celsius for temperatures)"
        ],
        "nutritional_info": {{
            "calories": "XXX kcal",
            "protein": "XX g",
            "carbs": "XX g",
            "fat": "XX g",
            "fiber": "XX g"
        }},
        "cooking_tips": "Helpful cooking tips and suggestions (use metric measurements: g, ml, cm, °C)",
        "cost_estimate": {{
            "total_cost": "Estimate the total cost in EUR (e.g., '12.50 EUR')",
            "cost_per_serving": "Calculate cost per serving in EUR (e.g., '3.10 EUR')",
            "cost_level": "One of: budget (under 15 EUR), moderate (15-30 EUR), expensive (over 30 EUR)"
        }}
    }}
    
    Make sure to:
    1. Include all the ingredients provided and respect the dietary preferences
    2. Use ONLY metric measurements:
       - Weight in grams (g) or kilograms (kg)
       - Volume in milliliters (ml) or liters (L)
       - Temperature in Celsius (°C)
       - Length in centimeters (cm)
    3. Calculate accurate nutritional information PER SERVING based on USDA values:
       - Calories: typically 300-800 kcal per serving for a main dish
       - Protein: typically 15-40g per serving for a main dish
       - Carbs: typically 30-60g per serving for a balanced meal
       - Fat: typically 10-30g per serving
       - Fiber: typically 4-10g per serving from vegetables, grains, legumes
    4. Double-check all nutritional calculations
    5. Account for cooking methods in nutritional values
    6. Include all ingredients in the nutritional calculation
    7. Use realistic measurements and cooking times
    8. All text should be in English"""

    completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a recipe generation AI. You must ONLY output valid JSON without any markdown formatting or additional text."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="mixtral-8x7b-32768",
        temperature=0.5,  # Reduced temperature for more consistent output
        max_tokens=4000
    )
    
    try:
        # Get and clean the response
        response_content = completion.choices[0].message.content.strip()
        
        # Debug logging
        print("\nRaw AI Response:")
        print("=" * 80)
        print(response_content)
        print("=" * 80)
        
        # Clean up any markdown or formatting
        response_content = response_content.replace('```json', '')
        response_content = response_content.replace('```', '')
        response_content = response_content.strip()
        
        print("\nCleaned Response:")
        print("=" * 80)
        print(response_content)
        print("=" * 80)
        
        # Try to parse JSON
        try:
            recipe_data = json.loads(response_content)
        except json.JSONDecodeError as e:
            print(f"\nJSON Parse Error: {str(e)}")
            print("Invalid JSON content:")
            print(response_content)
            return jsonify({
                'error': f'Failed to parse recipe data: {str(e)}',
                'raw_content': response_content[:1000]  # Limit response size
            }), 500
            
        # Ensure the recipe data has all required fields with default values
        structured_recipe = {
            "name": recipe_data.get("name", "Recipe"),
            "prep_time": recipe_data.get("prep_time", "N/A"),
            "cooking_time": recipe_data.get("cooking_time", "N/A"),
            "servings": recipe_data.get("servings", "N/A"),
            "ingredients": recipe_data.get("ingredients", []),
            "instructions": recipe_data.get("instructions", []),
            "nutritional_info": {
                "calories": recipe_data.get("nutritional_info", {}).get("calories", "N/A"),
                "protein": recipe_data.get("nutritional_info", {}).get("protein", "N/A"),
                "carbs": recipe_data.get("nutritional_info", {}).get("carbs", "N/A"),
                "fat": recipe_data.get("nutritional_info", {}).get("fat", "N/A")
            },
            "cooking_tips": recipe_data.get("cooking_tips", "No specific tips available."),
            "cost_estimate": {
                "total_cost": recipe_data.get("cost_estimate", {}).get("total_cost", "N/A"),
                "cost_per_serving": recipe_data.get("cost_estimate", {}).get("cost_per_serving", "N/A"),
                "cost_level": recipe_data.get("cost_estimate", {}).get("cost_level", "N/A")
            }
        }
        return jsonify(structured_recipe)
        
    except Exception as e:
        import traceback
        print(f"\nUnexpected Error: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        
        if hasattr(completion, 'choices') and len(completion.choices) > 0:
            print("\nAI Response Content:")
            print(completion.choices[0].message.content)
        
        return jsonify({
            'error': f'Failed to generate recipe: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

@app.route('/download_recipe', methods=['POST'])
def download_recipe():
    recipe_data = request.json
    
    # Create a PDF
    filename = f"recipe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(os.getcwd(), 'static', 'downloads', filename)
    
    # Ensure the downloads directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Create the PDF
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, recipe_data['name'])
    
    # Basic Info
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Prep Time: {recipe_data['prep_time']}")
    c.drawString(50, height - 100, f"Cooking Time: {recipe_data['cooking_time']}")
    c.drawString(50, height - 120, f"Servings: {recipe_data['servings']}")
    
    # Ingredients
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 160, "Ingredients:")
    c.setFont("Helvetica", 12)
    y = height - 180
    for ingredient in recipe_data['ingredients']:
        c.drawString(70, y, f"• {ingredient}")
        y -= 20
    
    # Instructions
    y -= 20
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Instructions:")
    c.setFont("Helvetica", 12)
    y -= 20
    for i, instruction in enumerate(recipe_data['instructions'], 1):
        # Split long instructions into multiple lines
        words = instruction.split()
        line = f"{i}. "
        lines = []
        for word in words:
            if len(line + " " + word) < 75:  # max line length
                line += " " + word
            else:
                lines.append(line)
                line = "   " + word  # indent continuation lines
        lines.append(line)
        
        for line in lines:
            c.drawString(70, y, line.strip())
            y -= 20
        y -= 10  # extra space between instructions
    
    # Nutritional Info
    y -= 20
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Nutritional Information:")
    c.setFont("Helvetica", 12)
    y -= 20
    nutritional_info = recipe_data['nutritional_info']
    c.drawString(70, y, f"Calories: {nutritional_info['calories']}")
    c.drawString(70, y - 20, f"Protein: {nutritional_info['protein']}")
    c.drawString(70, y - 40, f"Carbs: {nutritional_info['carbs']}")
    c.drawString(70, y - 60, f"Fat: {nutritional_info['fat']}")
    
    # Cooking Tips
    y -= 100
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Cooking Tips:")
    c.setFont("Helvetica", 12)
    
    # Split cooking tips into multiple lines
    words = recipe_data['cooking_tips'].split()
    line = ""
    y -= 20
    for word in words:
        if len(line + " " + word) < 75:  # max line length
            line += " " + word
        else:
            c.drawString(70, y, line.strip())
            y -= 20
            line = word
    if line:
        c.drawString(70, y, line.strip())
    
    c.save()
    
    return send_file(filepath, as_attachment=True, download_name=f"{recipe_data['name'].lower().replace(' ', '_')}.pdf")

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 3000)),
        debug=debug_mode
    )

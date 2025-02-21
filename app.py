from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
import os
import groq
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import re

# Unit conversion constants and functions
UNIT_CONVERSIONS = {
    # Volume
    'cup': {'ml': 236.588, 'l': 0.236588},
    'tbsp': {'ml': 14.7868, 'tsp': 3},
    'tsp': {'ml': 4.92892},
    'fl_oz': {'ml': 29.5735},
    'pint': {'ml': 473.176},
    'quart': {'ml': 946.353},
    'gallon': {'l': 3.78541},
    
    # Weight
    'oz': {'g': 28.3495},
    'lb': {'g': 453.592, 'kg': 0.453592},
    'g': {'oz': 0.035274},
    'kg': {'lb': 2.20462},
    
    # Temperature
    'F': {'C': lambda x: (x - 32) * 5/9},
    'C': {'F': lambda x: (x * 9/5) + 32}
}

def extract_number_and_unit(ingredient_str):
    """Extract number and unit from ingredient string."""
    # Pattern for finding numbers (including fractions) and units
    pattern = r'([\d./]+)\s*([a-zA-Z]+)'
    match = re.search(pattern, ingredient_str)
    if match:
        number_str, unit = match.groups()
        # Convert fraction to decimal if needed
        if '/' in number_str:
            num, denom = map(float, number_str.split('/'))
            number = num / denom
        else:
            number = float(number_str)
        return number, unit.lower()
    return None, None

def convert_unit(value, from_unit, to_unit):
    """Convert between units using the conversion table."""
    if from_unit == to_unit:
        return value
        
    if from_unit in UNIT_CONVERSIONS and to_unit in UNIT_CONVERSIONS[from_unit]:
        conversion = UNIT_CONVERSIONS[from_unit][to_unit]
        if callable(conversion):
            return conversion(value)
        return value * conversion
        
    # Try reverse conversion
    if to_unit in UNIT_CONVERSIONS and from_unit in UNIT_CONVERSIONS[to_unit]:
        conversion = UNIT_CONVERSIONS[to_unit][from_unit]
        if callable(conversion):
            return 1 / conversion(1/value)
        return value / conversion
        
    # Try conversion through a common unit (e.g., ml for volume)
    if from_unit in UNIT_CONVERSIONS and to_unit in UNIT_CONVERSIONS:
        common_units = set(UNIT_CONVERSIONS[from_unit].keys()) & \
                      set(unit for u in UNIT_CONVERSIONS.values() for unit in u.keys())
        if common_units:
            common_unit = next(iter(common_units))
            first_conversion = convert_unit(value, from_unit, common_unit)
            return convert_unit(first_conversion, common_unit, to_unit)
            
    return None

def format_measurement(value, unit):
    """Format a measurement value with appropriate precision."""
    if value < 0.1:
        return f"{value:.3f} {unit}"
    elif value < 1:
        return f"{value:.2f} {unit}"
    elif value % 1 == 0:
        return f"{int(value)} {unit}"
    else:
        return f"{value:.1f} {unit}"


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
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; font-src 'self' cdnjs.cloudflare.com; img-src 'self' data:;"
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
        '🐑 Lamb', '🦐 Shrimp', '🦀 Crab', '🐙 Octopus', '🦑 Squid', '🐠 Salmon',
        '🦞 Lobster', '🐠 Tuna', '🐟 Cod', '🐟 Trout', '🦪 Oysters', '🦪 Mussels',
        '🥓 Bacon', '🦃 Turkey Bacon', '🥩 Veal', '🐑 Mutton',
        '🐠 Sea Bass', '🐟 Halibut'
    ],
    'vegetables': [
        '🥕 Carrot', '🥦 Broccoli', '🍅 Tomato', '🥬 Lettuce', '🫑 Bell Pepper',
        '🧅 Onion', '🥒 Cucumber', '🍆 Eggplant', '🥔 Potato', '🍠 Sweet Potato',
        '🥗 Spinach', '🥬 Kale', '🌽 Corn', '🥜 Peanuts', '🫘 Beans', '🥜 Chickpeas',
        '🥦 Cauliflower', '🥬 Cabbage', '🍄 Mushroom', '🥝 Zucchini',
        '🥬 Swiss Chard', '🥬 Collard Greens', '🥬 Arugula', '🥕 Beets',
        '🧅 Leeks', '🥬 Watercress', '🥬 Endive', '🥕 Parsnips',
        '🥬 Radicchio', '🥬 Mustard Greens'
    ],
    'spices': [
        '🌶️ Chili', '🧄 Garlic', '🌿 Basil', '🌱 Oregano', '🍃 Thyme',
        '🧂 Salt', '⚫ Black Pepper', '🟡 Turmeric', '🟤 Cinnamon', '🟡 Ginger',
        '🟤 Cumin', '🟡 Curry Powder', '🔴 Paprika', '🟡 Saffron', '🌿 Rosemary',
        '🌿 Sage', '🌿 Mint', '🌶️ Cayenne', '⭐ Star Anise', '🟤 Nutmeg',
        '🟤 Cardamom', '🟤 Cloves', '🟡 Coriander', '🟡 Fenugreek', '🌶️ Szechuan Pepper',
        '🟤 Allspice', '🟡 Mustard Seeds', '🟤 Caraway', '🟡 Sumac', '🌶️ Wasabi'
    ],
    'grains': [
        '🍚 Rice', '🍝 Pasta', '🥖 Bread', '🌽 Corn', '🥣 Quinoa',
        '🥯 Bagel', '🥨 Pretzel', '🥜 Oats', '🌾 Barley', '🌾 Rye',
        '🥖 Sourdough', '🍝 Noodles', '🌾 Couscous', '🌾 Buckwheat', '🌾 Millet',
        '🌾 Amaranth', '🌾 Teff', '🌾 Sorghum', '🌾 Wild Rice', '🌾 Spelt',
        '🌾 Kamut', '🌾 Farro', '🍝 Orzo', '🌾 Triticale', '🥖 Pita'
    ],
    'dairy': [
        '🥚 Eggs', '🥛 Milk', '🧀 Cheese', '🧈 Butter', '🥛 Yogurt', '🥛 Cream',
        '🧀 Mozzarella', '🧀 Cheddar', '🧀 Parmesan', '🧀 Feta', '🥛 Sour Cream',
        '🧀 Brie', '🧀 Gouda', '🧀 Blue Cheese', '🧀 Ricotta', '🧀 Mascarpone',
        '🧀 Provolone', '🧀 Gruyere', '🧀 Camembert', '🥛 Kefir', '🧀 Halloumi'
    ],
    'fruits': [
        '🍎 Apple', '🍌 Banana', '🍊 Orange', '🍇 Grapes', '🍓 Strawberry',
        '🫐 Blueberry', '🥝 Kiwi', '🍍 Pineapple', '🥭 Mango', '🍑 Peach',
        '🍐 Pear', '🍒 Cherry', '🥥 Coconut', '🫐 Raspberry', '🍇 Blackberry',
        '🍊 Tangerine', '🍊 Clementine', '🥝 Dragon Fruit', '🍈 Cantaloupe', '🍈 Honeydew',
        '🍇 Plum', '🥭 Papaya', '🍊 Grapefruit', '🍇 Pomegranate', '🍑 Apricot'
    ],
    'herbs': [
        '🌿 Parsley', '🌿 Cilantro', '🌿 Dill', '🌿 Chives', '🌿 Tarragon',
        '🌿 Lemongrass', '🌿 Bay Leaf', '🌿 Marjoram', '🌿 Fennel', '🌿 Lavender',
        '🌿 Sorrel', '🌿 Borage', '🌿 Lovage', '🌿 Savory', '🌿 Hyssop',
        '🌿 Epazote', '🌿 Shiso', '🌿 Angelica', '🌿 Lemon Verbena', '🌿 Thai Basil'
    ],
    'nuts_seeds': [
        '🥜 Almonds', '🥜 Walnuts', '🥜 Cashews', '🌰 Hazelnuts', '🥜 Pistachios',
        '🌱 Chia Seeds', '🌱 Flax Seeds', '🌱 Sunflower Seeds', '🌱 Pumpkin Seeds', '🥜 Pine Nuts',
        '🥜 Macadamia', '🥜 Pecans', '🌱 Hemp Seeds', '🌱 Sesame Seeds', '🥜 Brazil Nuts',
        '🌱 Poppy Seeds', '🥜 Chestnuts', '🌱 Quinoa Seeds', '🌱 Amaranth Seeds', '🌱 Watermelon Seeds'
    ],
    'condiments': [
        '🥫 Ketchup', '🟡 Mustard', '🥫 Mayo', '🫒 Olive Oil', '🥢 Soy Sauce',
        '🍯 Honey', '🧂 Vinegar', '🥫 Hot Sauce', '🥫 BBQ Sauce', '🥫 Worcestershire',
        '🫒 Sesame Oil', '🥫 Fish Sauce', '🥫 Oyster Sauce', '🥫 Hoisin Sauce', '🥫 Teriyaki Sauce',
        '🫒 Avocado Oil', '🫒 Coconut Oil', '🥫 Sriracha', '🥫 Tahini', '🥫 Miso Paste'
    ],
    'sweeteners': [
        '🍫 Dark Chocolate', '🍫 Milk Chocolate', '🍫 White Chocolate', '🌸 Vanilla Bean', '🌸 Vanilla Extract',
        '🍯 Maple Syrup', '🍯 Agave Nectar', '🧂 Brown Sugar', '🧂 White Sugar', '🧂 Powdered Sugar',
        '🍯 Molasses', '🥥 Coconut Sugar', '🍯 Date Syrup', '🧂 Stevia', '🧂 Monk Fruit',
        '🍯 Rice Syrup', '🍯 Barley Malt', '🌺 Rose Water', '🌸 Orange Blossom Water', '🍫 Cocoa Powder',
        '🍫 Cacao Nibs', '🌸 Almond Extract', '🌸 Mint Extract', '🌸 Rum Extract', '🍯 Caramel Sauce'
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

@app.route('/convert_units', methods=['POST'])
def convert_units():
    data = request.json
    value = float(data['value'])
    from_unit = data['from_unit'].lower()
    to_unit = data['to_unit'].lower()
    
    result = convert_unit(value, from_unit, to_unit)
    if result is not None:
        return jsonify({
            'success': True,
            'result': format_measurement(result, to_unit)
        })
    return jsonify({
        'success': False,
        'error': f'Cannot convert from {from_unit} to {to_unit}'
    })

@app.route('/generate_recipe', methods=['POST'])
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

    prompt = f"""You are a professional nutritionist, chef, and sommelier AI. Generate a recipe using these ingredients: {', '.join(selected_ingredients)}. 
    Dietary preferences: {', '.join(dietary_prefs)}.
    {budget_prompt}
    
    For beverage pairings:
    1. Suggest 2-3 alcoholic beverages that complement the dish's flavors
    2. Explain why each beverage pairs well with the dish
    3. Suggest 2-3 non-alcoholic alternatives with explanations
    4. Consider the dish's intensity, flavors, and cooking method
    
    For serving sizes:
    1. Calculate exact portion sizes in grams
    2. Base number of servings on standard portion sizes
    3. Consider dish type (main course, side dish, dessert)
    4. Explain your serving size calculation
    
    When assessing recipe difficulty, carefully evaluate these criteria:

    1. Ingredients Accessibility:
       - EASY: Common ingredients found in any grocery store
       - MEDIUM: Some specialty ingredients but available in larger supermarkets
       - HARD: Requires visits to specialty stores or hard-to-find items

    2. Preparation Work:
       - EASY: Minimal chopping, no marinating, simple mixing
       - MEDIUM: Moderate prep work, some marinating, multiple components
       - HARD: Extensive chopping, long marination, complex prep steps

    3. Cooking Techniques:
       - EASY: Basic techniques like boiling, frying, roasting
       - MEDIUM: More skilled techniques like sauce-making, pastry work
       - HARD: Advanced techniques like sous-vide, complex baking, temperature control

    4. Time Investment:
       - EASY: Under 30 minutes active time
       - MEDIUM: 30-60 minutes active time
       - HARD: Over 60 minutes active time or requires precise timing

    5. Equipment Requirements:
       - EASY: Basic pots, pans, and utensils
       - MEDIUM: Food processor, mixer, or specialized pans
       - HARD: Specialized equipment or tools

    6. Instructions Complexity:
       - EASY: Under 5 steps, straightforward instructions
       - MEDIUM: 5-10 steps, some multitasking
       - HARD: Over 10 steps or complex multitasking

    Based on these criteria, you MUST classify EVERY recipe as one of:
    - EASY: Majority of criteria are easy, none are hard
    - MEDIUM: Mix of easy and medium criteria, at most one hard
    - HARD: Multiple hard criteria or requires significant skill

    You MUST provide a difficulty level for EVERY recipe - 'not specified' is not acceptable.
    Include a brief explanation of why you chose that difficulty level.
    
    IMPORTANT: 
    1. Your response must be ONLY valid JSON, with no additional text before or after.
    2. Do not include markdown code blocks or any other formatting.
    3. Do not escape underscores in field names - use them as is.
    4. You MUST include a difficulty assessment for EVERY recipe using the criteria above.
    5. The difficulty explanation should reference specific aspects from the criteria list.
    
    Return the recipe in this EXACT JSON format:
    {{
        "name": "Recipe Name",
        "prep_time": "XX minutes",
        "cooking_time": "XX minutes",
        "servings": {{
            "count": "X servings",
            "size_per_serving": "XXX grams",
            "total_weight": "XXX grams",
            "serving_note": "Brief explanation of serving size calculation"
        }},
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
            "fiber": "XX g",
            "sugar": "XX g",
            "sodium": "XXX mg",
            "cholesterol": "XX mg",
            "saturated_fat": "XX g",
            "trans_fat": "XX g",
            "vitamins": [
                "Vitamin A: XX% DV",
                "Vitamin C: XX% DV",
                "Vitamin D: XX% DV",
                "Iron: XX% DV",
                "Calcium: XX% DV"
            ]
        }},
        "cooking_tips": "Helpful cooking tips and suggestions (use metric measurements: g, ml, cm, °C)",
        "difficulty": {{
            "level": "One of: easy, medium, hard",
            "explanation": "Brief explanation based on ingredients, prep work, techniques, time, equipment, and steps complexity"
        }},
        "cost_estimate": {{
            "total_cost": "Estimate the total cost in EUR (e.g., '12.50 EUR')",
            "cost_per_serving": "Calculate cost per serving in EUR (e.g., '3.10 EUR')",
            "cost_level": "One of: budget (under 15 EUR), moderate (15-30 EUR), expensive (over 30 EUR)"
        }},
        "beverage_pairings": {{
            "alcoholic": [
                "Suggested alcoholic beverage 1 with brief explanation",
                "Suggested alcoholic beverage 2 with brief explanation"
            ],
            "non_alcoholic": [
                "Suggested non-alcoholic beverage 1 with brief explanation",
                "Suggested non-alcoholic beverage 2 with brief explanation"
            ]
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
            "servings": {
                "count": recipe_data.get("servings", {}).get("count", "N/A"),
                "size_per_serving": recipe_data.get("servings", {}).get("size_per_serving", "N/A"),
                "total_weight": recipe_data.get("servings", {}).get("total_weight", "N/A"),
                "serving_note": recipe_data.get("servings", {}).get("serving_note", "No serving size explanation available.")
            },
            "ingredients": recipe_data.get("ingredients", []),
            "instructions": recipe_data.get("instructions", []),
            "nutritional_info": {
                "calories": recipe_data.get("nutritional_info", {}).get("calories", "N/A"),
                "protein": recipe_data.get("nutritional_info", {}).get("protein", "N/A"),
                "carbs": recipe_data.get("nutritional_info", {}).get("carbs", "N/A"),
                "fat": recipe_data.get("nutritional_info", {}).get("fat", "N/A")
            },
            "cooking_tips": recipe_data.get("cooking_tips", "No specific tips available."),
            "difficulty": {
                "level": recipe_data.get("difficulty", {}).get("level", "N/A"),
                "explanation": recipe_data.get("difficulty", {}).get("explanation", "No difficulty explanation available.")
            },
            "cost_estimate": {
                "total_cost": recipe_data.get("cost_estimate", {}).get("total_cost", "N/A"),
                "cost_per_serving": recipe_data.get("cost_estimate", {}).get("cost_per_serving", "N/A"),
                "cost_level": recipe_data.get("cost_estimate", {}).get("cost_level", "N/A")
            },
            "beverage_pairings": {
                "alcoholic": recipe_data.get("beverage_pairings", {}).get("alcoholic", ["No alcoholic pairings available"]),
                "non_alcoholic": recipe_data.get("beverage_pairings", {}).get("non_alcoholic", ["No non-alcoholic pairings available"])
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

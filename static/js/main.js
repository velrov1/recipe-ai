// Function to update nutritional information
function updateNutritionalInfo(nutritionData) {
    // Update main macronutrients
    document.getElementById('recipeCalories').textContent = `${nutritionData.calories || 0} kcal`;
    document.getElementById('recipeProtein').textContent = `${nutritionData.protein || 0}g`;
    document.getElementById('recipeCarbs').textContent = `${nutritionData.carbs || 0}g`;
    document.getElementById('recipeFat').textContent = `${nutritionData.fat || 0}g`;
    document.getElementById('recipeFiber').textContent = `${nutritionData.fiber || 0}g`;

    // Update additional nutrients
    document.getElementById('recipeSugar').textContent = `${nutritionData.sugar || 0}g`;
    document.getElementById('recipeSodium').textContent = `${nutritionData.sodium || 0}mg`;
    document.getElementById('recipeCholesterol').textContent = `${nutritionData.cholesterol || 0}mg`;
    document.getElementById('recipeSaturatedFat').textContent = `${nutritionData.saturatedFat || 0}g`;
    document.getElementById('recipeTransFat').textContent = `${nutritionData.transFat || 0}g`;

    // Update vitamins
    const vitaminsContainer = document.getElementById('recipeVitamins');
    vitaminsContainer.innerHTML = ''; // Clear existing content

    if (nutritionData.vitamins) {
        Object.entries(nutritionData.vitamins).forEach(([vitamin, percentage]) => {
            const vitaminElement = document.createElement('div');
            vitaminElement.className = 'flex justify-between items-center';
            vitaminElement.innerHTML = `
                <span class="text-gray-600">${vitamin}</span>
                <div class="flex items-center">
                    <div class="w-24 h-2 bg-gray-200 rounded-full mr-2">
                        <div class="h-full bg-indigo-600 rounded-full" style="width: ${percentage}%"></div>
                    </div>
                    <span class="font-medium">${percentage}%</span>
                </div>
            `;
            vitaminsContainer.appendChild(vitaminElement);
        });
    }
}

// Timer functionality
let timerInterval;
const timerSound = document.getElementById('timerSound');

function startTimer(duration) {
    clearInterval(timerInterval);
    let timeLeft = duration * 60; // Convert minutes to seconds

    timerInterval = setInterval(() => {
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            playTimerSound();
            return;
        }

        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        
        document.getElementById('timer').textContent = 
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        timeLeft--;
    }, 1000);
}

function playTimerSound() {
    if (timerSound) {
        timerSound.play().catch(error => {
            console.log('Error playing timer sound:', error);
        });
    }
}

// Event listener for timer form
document.getElementById('timerForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const minutes = parseInt(document.getElementById('timerInput').value);
    if (!isNaN(minutes) && minutes > 0) {
        startTimer(minutes);
    }
});

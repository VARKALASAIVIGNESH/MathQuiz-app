from flask import Flask, render_template, request, jsonify
from firebase_admin import credentials, initialize_app, messaging
import random
from apscheduler.schedulers.background import BackgroundScheduler
import os
from flask_cors import CORS  # Import CORS after Flask

app = Flask(__name__)

# Enable CORS for your app
CORS(app)  # This line should come after the app definition

# Initialize Firebase Admin SDK
cred = credentials.Certificate("FCM.json")  # Replace with your actual Firebase credentials file
initialize_app(cred)

# In-memory storage for questions and scores
questions = []
scores = {}

# Default route to render index.html
@app.route('/')
def home():
    return render_template('index.html')  # Flask will automatically look in the 'templates' folder

# Favicon handler (for avoiding errors in the browser console)
@app.route('/favicon.ico')
def favicon():
    return '', 204

# Generate a random tough math question
def generate_question():
    operations = ['+', '-', '*', '/', '**', 'cube']
    num1 = random.randint(10, 99)  # 2-digit numbers
    num2 = random.randint(10, 99)  # 2-digit numbers
    operation = random.choice(operations)
    
    if operation == '+':
        question = f"{num1} + {num2}"
        answer = num1 + num2
    elif operation == '-':
        question = f"{num1} - {num2}"
        answer = num1 - num2
    elif operation == '*':
        question = f"{num1} * {num2}"
        answer = num1 * num2
    elif operation == '/':
        # Prevent division by zero
        num2 = random.randint(1, 99)
        question = f"{num1} / {num2}"
        answer = round(num1 / num2, 2)  # Keep answer with 2 decimal points
    elif operation == '**':  # Square
        num = random.randint(10, 99)  # 2-digit number
        question = f"{num} squared (i.e., {num}^2)"
        answer = num ** 2
    elif operation == 'cube':  # Cube
        num = random.randint(3, 10)  # Lower range for cubes (3-digit cubes would be too large)
        question = f"Cube of {num} (i.e., {num}^3)"
        answer = num ** 3
    
    return {"question": question, "answer": answer}


# API to get a new question
@app.route('/generate-question', methods=['POST'])
def new_question():
    question_data = generate_question()
    questions.append(question_data)
    return jsonify({"question": question_data['question']}), 200


# API to submit an answer
@app.route('/submit-answer', methods=['POST'])
def submit_answer():
    data = request.json
    question = data.get('question')
    user_answer = float(data.get('answer'))
    user = data.get('user')  # Get the user identifier

    # Find the question and validate the answer
    for q in questions:
        if q['question'] == question:
            correct = q['answer'] == user_answer
            # Update the score for the user
            if correct:
                scores[user] = scores.get(user, 0) + 1
            else:
                scores[user] = scores.get(user, 0)
            # Return response with score and correctness status
            return jsonify({"correct": correct, "score": scores[user]}), 200
    
    return jsonify({"error": "Question not found"}), 404


# Send a notification (using Firebase FCM)
def send_notification():
    question_data = generate_question()
    message = messaging.Message(
        notification=messaging.Notification(
            title="New Math Question!",
            body=f"Question: {question_data['question']}"
        ),
        topic="all_users",  # Broadcast to all users
    )
    # This sends the notification to all users who are subscribed to the "all_users" topic
    try:
        response = messaging.send(message)
        print(f"Successfully sent message: {response}")
    except Exception as e:
        print(f"Error sending message: {e}")



# Schedule notifications (using APScheduler)
scheduler = BackgroundScheduler()
scheduler.add_job(send_notification, 'interval', hours=1)  # Send a notification every hour
scheduler.start()


# Start the Flask app, bind to port dynamically for Heroku (or localhost)
if __name__ == '__main__':
    # For local testing or deployment to platforms like Heroku
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

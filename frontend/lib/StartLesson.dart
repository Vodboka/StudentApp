// ignore_for_file: file_names

import 'package:flutter/material.dart';
//TODO work on the counter so it modifies only after the user pressed the next button with a correct answer
//TODO implement a validate button, and transform into a next button after the colour green was displayed
//TODO repeat the questions that were not validated in the end

class StartLesson extends StatefulWidget {
  @override
  _StartLesson createState() => _StartLesson();
}

class _StartLesson extends State<StartLesson> {
  int currentQuestionIndex = 0;
  int correctAnswers = 0;
  int? selectedAnswerIndex;

  // List of questions, each question has text, multiple choices, and the correct answer index
  List<Map<String, dynamic>> questions = [
    {
      'question': 'What is 2 + 2?',
      'choices': ['3', '4', '5', '6'],
      'correctAnswerIndex': 1,
    },
    {
      'question': 'What is the capital of France?',
      'choices': ['London', 'Berlin', 'Paris', 'Madrid'],
      'correctAnswerIndex': 2,
    },
    {
      'question': 'Which animal is the largest?',
      'choices': ['Elephant', 'Giraffe', 'Whale', 'Lion'],
      'correctAnswerIndex': 2,
    },
  ];

  void checkAnswer(int selectedIndex) {
    setState(() {
      selectedAnswerIndex = selectedIndex;
      if (selectedIndex == questions[currentQuestionIndex]['correctAnswerIndex']) {
        correctAnswers++;
      }
    });
  }

  void nextQuestion() {
    setState(() {
      if (currentQuestionIndex < questions.length - 1) {
        currentQuestionIndex++;
        selectedAnswerIndex = null; // Reset the selected answer
      } else {
        // If no more questions, reset or finish the quiz
        currentQuestionIndex = 0;
        selectedAnswerIndex = null;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    // Calculate the progress
    double progress = (currentQuestionIndex + 1) / questions.length;

    return Scaffold(
      appBar: AppBar(
        title: Text("Lesson"),
      ),
      body: SingleChildScrollView( // Wrap the content in a scrollable view
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch, // Ensures that the button stretches
          mainAxisAlignment: MainAxisAlignment.start,
          children: <Widget>[
            // Progress Bar
            LinearProgressIndicator(
              value: progress,
              minHeight: 8,
              backgroundColor: const Color.fromARGB(255, 224, 224, 224),
              color: const Color.fromARGB(255, 254, 136, 51),
            ),
            SizedBox(height: 20),
            // Question Text
            Text(
              questions[currentQuestionIndex]['question'],
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 20),
            // Choices as buttons
            ...List.generate(questions[currentQuestionIndex]['choices'].length, (index) {
              bool isSelected = selectedAnswerIndex == index;
              bool isCorrect = isSelected && index == questions[currentQuestionIndex]['correctAnswerIndex'];
              bool isIncorrect = isSelected && index != questions[currentQuestionIndex]['correctAnswerIndex'];

              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 8.0),
                child: ElevatedButton(
                  onPressed: () {
                    checkAnswer(index);
                  },
                  style: ButtonStyle(
                    backgroundColor: WidgetStateProperty.all(
                      isCorrect
                          ? Colors.green // Correct answer highlighted in green
                          : isIncorrect
                              ? Colors.red // Incorrect answer highlighted in red
                              : const Color.fromARGB(255, 255, 195, 106), // Default answer button
                    ),
                    shape: WidgetStateProperty.all(RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    )),
                  ),
                  child: Text(
                    questions[currentQuestionIndex]['choices'][index],
                    style: TextStyle(fontSize: 18),
                  ),
                ),
              );
            }),
            SizedBox(height: 20),
            // Spacer widget ensures the Next button stays at the bottom
            SizedBox(height: 20),
            Padding(
              padding: EdgeInsets.only(bottom: 16),
              child: ElevatedButton(
                onPressed: nextQuestion,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.deepOrange, // A distinct color for the Next button
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  padding: EdgeInsets.symmetric(vertical: 15),
                  minimumSize: Size(double.infinity, 0), // Make the button stretch across
                ),
                child: Text(
                  'Next',
                  style: TextStyle(fontSize: 18),
                ),
              ),
            ),
            // Correct answers display (optional, can be removed or customized)
            Text(
              'Correct Answers: $correctAnswers',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

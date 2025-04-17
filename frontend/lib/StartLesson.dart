// ignore_for_file: file_names

import 'package:flutter/material.dart';

class StartLesson extends StatefulWidget {
  @override
  _StartLesson createState() => _StartLesson();
}

class _StartLesson extends State<StartLesson> {
  int currentQuestionIndex = 0;
  int correctAnswers = 0;
  int? selectedAnswerIndex;
  bool isAnswerChecked = false;

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

  void validateAnswer() {
    if (selectedAnswerIndex == null || isAnswerChecked) return;

    setState(() {
      isAnswerChecked = true;

      if (selectedAnswerIndex == questions[currentQuestionIndex]['correctAnswerIndex']) {
        correctAnswers++;
      }
    });
  }

  void nextQuestion() {
    if (!isAnswerChecked) return;

    setState(() {
      if (currentQuestionIndex < questions.length - 1) {
        currentQuestionIndex++;
        selectedAnswerIndex = null;
        isAnswerChecked = false;
      } else {
        // Quiz done: Optionally handle completion
        // For now, we'll restart
        currentQuestionIndex = 0;
        selectedAnswerIndex = null;
        isAnswerChecked = false;
        correctAnswers = 0;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    double progress = (currentQuestionIndex + 1) / questions.length;

    return Scaffold(
      appBar: AppBar(
        title: Text("Lesson"),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            LinearProgressIndicator(
              value: progress,
              minHeight: 8,
              backgroundColor: const Color.fromARGB(255, 224, 224, 224),
              color: const Color.fromARGB(255, 254, 136, 51),
            ),
            SizedBox(height: 20),
            Text(
              questions[currentQuestionIndex]['question'],
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 20),
            ...List.generate(questions[currentQuestionIndex]['choices'].length, (index) {
              bool isSelected = selectedAnswerIndex == index;
              bool isCorrect = isAnswerChecked && index == questions[currentQuestionIndex]['correctAnswerIndex'];
              bool isIncorrect = isAnswerChecked && isSelected && !isCorrect;

              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 8.0),
                child: ElevatedButton(
                  onPressed: isAnswerChecked
                      ? null
                      : () {
                          setState(() {
                            selectedAnswerIndex = index;
                          });
                        },
                  style: ButtonStyle(
                    backgroundColor: WidgetStateProperty.all(
                      isCorrect
                          ? Colors.green
                          : isIncorrect
                              ? Colors.red
                              : (isSelected
                                  ? const Color.fromARGB(255, 255, 195, 106)
                                  : Colors.grey[300]),
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

            // Validate / Next button
            Padding(
              padding: EdgeInsets.only(bottom: 16),
              child: ElevatedButton(
                onPressed: isAnswerChecked ? nextQuestion : validateAnswer,
                style: ElevatedButton.styleFrom(
                  backgroundColor: isAnswerChecked ? Colors.deepOrange : Colors.blue,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  padding: EdgeInsets.symmetric(vertical: 15),
                  minimumSize: Size(double.infinity, 0),
                ),
                child: Text(
                  isAnswerChecked ? 'Next' : 'Check',
                  style: TextStyle(fontSize: 18),
                ),
              ),
            ),

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

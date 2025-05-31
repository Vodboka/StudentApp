// ignore_for_file: file_names

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/material.dart';

class StartLesson extends StatefulWidget {
  final int lessonNumber;
  final String hash;

  StartLesson({required this.lessonNumber, required this.hash});

  @override
  _StartLesson createState() => _StartLesson();
}

class LessonService {
  static const String baseUrl = 'http://10.0.2.2:5000';

  Future<List<Map<String, dynamic>>?> fetchQuestions(String hash, int lessonNumber) async {
    final uri = Uri.parse('$baseUrl/get_lesson_questions')
        .replace(queryParameters: {
      'hash': hash,
      'lesson_number': lessonNumber.toString(),
    });

    final response = await http.get(uri);

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final questions = data['questions'];

      if (questions is List) {
        return questions
            .map<Map<String, dynamic>>((item) => Map<String, dynamic>.from(item))
            .toList();
      } else {
        print('Unexpected response format.');
        return null;
      }
    } else {
      print('Error fetching lesson questions: ${response.body}');
      return null;
    }
  }
}

class _StartLesson extends State<StartLesson> {
  int currentQuestionIndex = 0;
  int correctAnswers = 0;
  int? selectedAnswerIndex;
  bool isAnswerChecked = false;
  bool isLoading = true;
  bool quizCompleted = false;

  List<Map<String, dynamic>> questions = [];
  List<Map<String, dynamic>> incorrectQuestions = [];

  @override
  void initState() {
    super.initState();
    loadQuestions();
  }

  void loadQuestions() async {
    setState(() {
      isLoading = true;
    });

    final lessonService = LessonService();
    final fetchedQuestions =
        await lessonService.fetchQuestions(widget.hash, widget.lessonNumber);

    if (fetchedQuestions != null) {
      setState(() {
        questions = fetchedQuestions;
        currentQuestionIndex = 0;
        correctAnswers = 0;
        selectedAnswerIndex = null;
        isAnswerChecked = false;
        isLoading = false;
        incorrectQuestions.clear();
        quizCompleted = false;
      });
    } else {
      setState(() {
        isLoading = false;
      });
    }
  }

  void validateAnswer() {
    if (selectedAnswerIndex == null || isAnswerChecked) return;

    setState(() {
      isAnswerChecked = true;

      if (selectedAnswerIndex == questions[currentQuestionIndex]['correct_answer']) {
        correctAnswers++;
      } else {
        incorrectQuestions.add(questions[currentQuestionIndex]);
      }
    });
  }

  void nextQuestion() {
    if (!isAnswerChecked) return;

    setState(() {
      if (correctAnswers >= 15) {
        quizCompleted = true;
        return;
      }

      if (currentQuestionIndex < questions.length - 1) {
        currentQuestionIndex++;
      } else if (incorrectQuestions.isNotEmpty) {
        questions = List.from(incorrectQuestions);
        incorrectQuestions.clear();
        currentQuestionIndex = 0;
      } else {
        quizCompleted = true;
        return;
      }

      selectedAnswerIndex = null;
      isAnswerChecked = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Scaffold(
        appBar: AppBar(title: Text("Lesson ${widget.lessonNumber + 1}")),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (questions.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text("Lesson ${widget.lessonNumber + 1}")),
        body: Center(child: Text("No questions available")),
      );
    }

    if (quizCompleted) {
      return Scaffold(
        appBar: AppBar(title: Text("Lesson ${widget.lessonNumber + 1}")),
        body: Center(
          child: Text(
            "Lesson Complete!\nCorrect Answers: $correctAnswers",
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    double progress = (currentQuestionIndex + 1) / questions.length;

    return Scaffold(
      appBar: AppBar(title: Text("Lesson ${widget.lessonNumber + 1}")),
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
              bool isCorrect = isAnswerChecked && index == questions[currentQuestionIndex]['correct_answer'];
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
                    backgroundColor: MaterialStateProperty.all(
                      isCorrect
                          ? Colors.green
                          : isIncorrect
                              ? Colors.red
                              : (isSelected
                                  ? const Color.fromARGB(255, 255, 195, 106)
                                  : Colors.grey[300]),
                    ),
                    shape: MaterialStateProperty.all(RoundedRectangleBorder(
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

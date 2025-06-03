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

    try {
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
    } catch (e) {
      print('Network error fetching lesson questions: $e');
      return null;
    }
  }

  // New method to save updated question stats to the server
  Future<bool> saveQuestionStats(
      String hash,
      int lessonNumber,
      int questionIndex,
      int numberOfTries,
      int numberOfCorrectTries) async {
    final uri = Uri.parse('$baseUrl/update_question_stats');
    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'hash': hash,
          'lesson_number': lessonNumber,
          'question_index': questionIndex,
          'number_of_tries': numberOfTries,
          'number_of_correct_tries': numberOfCorrectTries,
        }),
      );

      if (response.statusCode == 200) {
        print('Question stats updated successfully on server.');
        return true;
      } else {
        print('Failed to update question stats on server: ${response.body}');
        return false;
      }
    } catch (e) {
      print('Network error saving question stats: $e');
      return false;
    }
  }
}

class _StartLesson extends State<StartLesson> {
  int currentQuestionIndex = 0;
  int overallCorrectAnswers = 0;
  int? selectedAnswerIndex;
  bool isAnswerChecked = false;
  bool isLoading = true;
  bool quizCompleted = false;

  List<Map<String, dynamic>> questions = [];
  List<Map<String, dynamic>> incorrectQuestions = [];

  final LessonService _lessonService = LessonService(); // Instance of LessonService

  @override
  void initState() {
    super.initState();
    loadQuestions();
  }

  void loadQuestions() async {
    setState(() {
      isLoading = true;
    });

    final fetchedQuestions =
        await _lessonService.fetchQuestions(widget.hash, widget.lessonNumber);

    if (fetchedQuestions != null) {
      setState(() {
        questions = fetchedQuestions;
        for (var q in questions) {
          q['number_of_tries'] ??= 0;
          q['number_of_correct_tries'] ??= 0;
        }
        currentQuestionIndex = 0;
        overallCorrectAnswers = 0;
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

      Map<String, dynamic> currentQuestion = questions[currentQuestionIndex];

      currentQuestion['number_of_tries'] = (currentQuestion['number_of_tries'] ?? 0) + 1;

      if (selectedAnswerIndex == currentQuestion['correct_answer']) {
        overallCorrectAnswers++;
        currentQuestion['number_of_correct_tries'] = (currentQuestion['number_of_correct_tries'] ?? 0) + 1;
      } else {
        incorrectQuestions.add(currentQuestion);
      }
      
      // Save the updated stats to the server immediately after validation
      _lessonService.saveQuestionStats(
        widget.hash,
        widget.lessonNumber,
        currentQuestionIndex, // Pass the index of the question in the current lesson's list
        currentQuestion['number_of_tries'],
        currentQuestion['number_of_correct_tries'],
      );
    });
  }

  void nextQuestion() {
    if (!isAnswerChecked) return;

    setState(() {
      if (overallCorrectAnswers >= 15) {
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
            "Lesson Complete!\nOverall Correct Answers: $overallCorrectAnswers",
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    Map<String, dynamic> currentQuestion = questions[currentQuestionIndex];
    int currentQuestionTries = currentQuestion['number_of_tries'] ?? 0;
    int currentQuestionCorrectTries = currentQuestion['number_of_correct_tries'] ?? 0;

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
              currentQuestion['question'],
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 20),
            ...List.generate(currentQuestion['choices'].length, (index) {
              bool isSelected = selectedAnswerIndex == index;
              bool isCorrect = isAnswerChecked && index == currentQuestion['correct_answer'];
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
                    currentQuestion['choices'][index],
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
              'Overall Correct Answers: $overallCorrectAnswers',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 10),
            Text(
              'Current Question Tries: $currentQuestionTries',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
              textAlign: TextAlign.center,
            ),
            Text(
              'Current Question Correct Tries: $currentQuestionCorrectTries',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

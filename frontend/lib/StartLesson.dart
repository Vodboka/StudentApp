// ignore_for_file: file_names
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/material.dart';

class StartLesson extends StatefulWidget {
  final String lessonName;
  final String subject;

  StartLesson({required this.lessonName, required this.subject});

  @override
  _StartLesson createState() => _StartLesson();
}

class LessonService {
  static const String baseUrl = 'http://10.0.2.2:5000';

  Future<String?> fetchLessonHash({
    required String lessonName,
    required String subject,
  }) async {
    final uri = Uri.parse('$baseUrl/get_lesson_hash').replace(queryParameters: {
      'lesson_name': lessonName,
      'subject': subject,
    });

    final response = await http.get(uri);

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['lesson hash'] as String?;
    } else {
      print('Error fetching lesson hash: ${response.body}');
      return null;
    }
  }

  Future<List<Map<String, dynamic>>?> fetchProcessedFile(String hashcode) async {
    final uri = Uri.parse('$baseUrl/get_processed_file/$hashcode');

    final response = await http.get(uri);

    if (response.statusCode == 200) {
      final data = json.decode(response.body);

      if (data is List) {
        return data.map<Map<String, dynamic>>((item) => Map<String, dynamic>.from(item)).toList();
      } else {
        print('Unexpected JSON format: expected a list');
        return null;
      }
    } else {
      print('Error fetching processed file: ${response.body}');
      return null;
    }
  }

  Future<List<Map<String, dynamic>>?> getQuestionsForLesson({
    required String lessonName,
    required String subject,
  }) async {
    final hash = await fetchLessonHash(lessonName: lessonName, subject: subject);
    if (hash == null) {
      print('Could not fetch lesson hash');
      return null;
    }
    return await fetchProcessedFile(hash);
  }
}

class _StartLesson extends State<StartLesson> {
  int currentQuestionIndex = 0;
  int correctAnswers = 0;
  int? selectedAnswerIndex;
  bool isAnswerChecked = false;
  bool isLoading = true;

  List<Map<String, dynamic>> questions = [];

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

    final fetchedQuestions = await lessonService.getQuestionsForLesson(
      lessonName: widget.lessonName,
      subject: widget.subject,
    );

    if (fetchedQuestions != null) {
      setState(() {
        questions = fetchedQuestions;
        currentQuestionIndex = 0;
        correctAnswers = 0;
        selectedAnswerIndex = null;
        isAnswerChecked = false;
        isLoading = false;
      });
    } else {
      // Could not fetch questions — handle error or fallback
      setState(() {
        isLoading = false;
      });
      // Optionally show an error dialog/snackbar here
    }
  }

  void validateAnswer() {
    if (selectedAnswerIndex == null || isAnswerChecked) return;

    setState(() {
      isAnswerChecked = true;

      if (selectedAnswerIndex == questions[currentQuestionIndex]['correct_answer']) {
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
        // Quiz finished - restart or handle differently
        currentQuestionIndex = 0;
        selectedAnswerIndex = null;
        isAnswerChecked = false;
        correctAnswers = 0;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Scaffold(
        appBar: AppBar(title: Text("Lesson")),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (questions.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text("Lesson")),
        body: Center(child: Text("No questions available")),
      );
    }

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
